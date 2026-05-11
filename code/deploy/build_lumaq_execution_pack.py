from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STACK_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = STACK_ROOT.parent
OUT_OPS = STACK_ROOT / "out" / "ops"

LUMAQ_REPORT_JSON = OUT_OPS / "lumaq_brain_report.json"
INSTITUTIONAL_TOP10_CSV = STACK_ROOT / "out" / "execution" / "institutional_top10.csv"
TRINITY_TOP10_CSV = WORKSPACE_ROOT / "trinity_v3_out" / "trinity_v3_top10.csv"
SHARPE_SURVIVORS_CSV = WORKSPACE_ROOT / "output" / "sharpe_pipeline_results_upgrade_survivors.csv"
SHARPE_DEBUG_REPORT_TXT = WORKSPACE_ROOT / "truth_master_pack" / "sharpe_pipeline_upgrade_report.txt"
SPORTS_ALPHA_JSON = STACK_ROOT / "out" / "sports_intelligence" / "_dk_alpha_board.json"

TOP10_REGISTRY_JSON = OUT_OPS / "lumaq_top10_alpha_registry.json"
TOP10_REGISTRY_MD = OUT_OPS / "lumaq_top10_alpha_registry.md"
STAGE_SCRIPT_MD = OUT_OPS / "lumaq_stage_script_3min.md"
BURNDOWN_MD = OUT_OPS / "lumaq_5_day_burndown.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            return [row for row in csv.DictReader(handle)]
    except Exception:
        return []


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def parse_debug_sharpe_rows(report_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^\s*(?P<strategy>[A-Za-z0-9_]+)\s+"
        r"(?P<sharpe>-?\d+(?:\.\d+)?)\s+"
        r"(?P<max_dd>-?\d+(?:\.\d+)?)\s+"
        r"(?P<final>-?\d+(?:\.\d+)?)\s+"
        r"(?P<pair>[A-Za-z0-9_/.-]+)\s+"
        r"(?P<mc_sharpe>-?\d+(?:\.\d+)?)\s+"
        r"(?P<score>-?\d+(?:\.\d+)?)\s*$"
    )
    for raw in report_text.splitlines():
        line = raw.rstrip()
        match = pattern.match(line)
        if not match:
            continue
        payload = match.groupdict()
        rows.append(
            {
                "strategy": payload["strategy"],
                "pair": payload["pair"],
                "sharpe": safe_float(payload["sharpe"]),
                "mc_sharpe": safe_float(payload["mc_sharpe"]),
                "max_dd": safe_float(payload["max_dd"]),
                "score": safe_float(payload["score"]),
                "validation": "debug_only_not_reality_passed",
            }
        )
    return rows


def rank_institutional(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda r: (
            safe_float(r.get("institutional_score")),
            safe_float(r.get("test_sharpe")),
            safe_float(r.get("wf_sharpe_mean")),
        ),
        reverse=True,
    )
    output: list[dict[str, Any]] = []
    for idx, row in enumerate(ranked[:10], start=1):
        output.append(
            {
                "rank": idx,
                "flow": row.get("flow", ""),
                "strategy": row.get("strategy", ""),
                "algo": row.get("algo", ""),
                "test_sharpe": safe_float(row.get("test_sharpe")),
                "wf_sharpe_mean": safe_float(row.get("wf_sharpe_mean")),
                "institutional_score": safe_float(row.get("institutional_score")),
                "deployment_score": safe_float(row.get("deployment_score")),
            }
        )
    return output


def rank_trinity(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda r: (safe_float(r.get("sharpe")), safe_float(r.get("score"))),
        reverse=True,
    )
    output: list[dict[str, Any]] = []
    for idx, row in enumerate(ranked[:10], start=1):
        output.append(
            {
                "rank": idx,
                "family": row.get("family", ""),
                "p1": row.get("p1", ""),
                "p2": row.get("p2", ""),
                "threshold": safe_float(row.get("threshold")),
                "score": safe_float(row.get("score")),
                "sharpe": safe_float(row.get("sharpe")),
                "max_dd": safe_float(row.get("max_dd")),
                "win_rate": safe_float(row.get("win_rate")),
            }
        )
    return output


def rank_sharpe_survivors(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    valid_rows = [r for r in rows if str(r.get("strategy", "")).strip()]
    ranked = sorted(
        valid_rows,
        key=lambda r: (safe_float(r.get("mc_sharpe")), safe_float(r.get("sharpe"))),
        reverse=True,
    )
    output: list[dict[str, Any]] = []
    for idx, row in enumerate(ranked[:10], start=1):
        output.append(
            {
                "rank": idx,
                "strategy": row.get("strategy", ""),
                "pair": row.get("pair", ""),
                "sharpe": safe_float(row.get("sharpe")),
                "mc_sharpe": safe_float(row.get("mc_sharpe")),
                "max_dd": safe_float(row.get("max_dd")),
                "score": safe_float(row.get("score")),
                "validation": "reality_passed",
            }
        )
    return output


def rank_sports_alpha(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    ranked = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: (safe_float(r.get("alpha_score_v2")), safe_float(r.get("edge_pct"))),
        reverse=True,
    )
    output: list[dict[str, Any]] = []
    for idx, row in enumerate(ranked[:10], start=1):
        output.append(
            {
                "rank": idx,
                "pick": row.get("pick", ""),
                "game": row.get("game", ""),
                "edge_pct": safe_float(row.get("edge_pct")),
                "alpha_score_v2": safe_float(row.get("alpha_score_v2")),
                "kelly_go_stake": safe_float(row.get("kelly_go_stake")),
                "flowform_count": int(safe_float(row.get("flowform_count"), 0.0)),
                "commence_time": row.get("commence_time", ""),
            }
        )
    return output


def rank_lumaq_blockers(report: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = report.get("micro_agent", {}).get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
    priority_map = {"critical": 0, "warn": 1, "info": 2}
    ranked = sorted(
        [t for t in tasks if isinstance(t, dict)],
        key=lambda t: (priority_map.get(str(t.get("priority", "warn")).lower(), 3), str(t.get("task", ""))),
    )
    output: list[dict[str, Any]] = []
    for idx, task in enumerate(ranked[:10], start=1):
        output.append(
            {
                "rank": idx,
                "priority": str(task.get("priority", "warn")).lower(),
                "source": task.get("source", ""),
                "task": task.get("task", ""),
                "detail": task.get("detail", ""),
                "target": task.get("target", ""),
            }
        )
    return output


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def build_registry(report: dict[str, Any]) -> dict[str, Any]:
    institutional = rank_institutional(read_csv(INSTITUTIONAL_TOP10_CSV))
    trinity = rank_trinity(read_csv(TRINITY_TOP10_CSV))
    survivors = rank_sharpe_survivors(read_csv(SHARPE_SURVIVORS_CSV))
    debug_rows = parse_debug_sharpe_rows(SHARPE_DEBUG_REPORT_TXT.read_text(encoding="utf-8", errors="ignore") if SHARPE_DEBUG_REPORT_TXT.exists() else "")
    sports = rank_sports_alpha(read_json(SPORTS_ALPHA_JSON, {}))
    blockers = rank_lumaq_blockers(report)

    return {
        "schema": "lumaq_top10_alpha_registry_v1",
        "generated_utc": now_utc(),
        "workspace_root": str(WORKSPACE_ROOT),
        "stack_root": str(STACK_ROOT),
        "source_files": {
            "institutional_top10_csv": str(INSTITUTIONAL_TOP10_CSV),
            "trinity_top10_csv": str(TRINITY_TOP10_CSV),
            "sharpe_survivors_csv": str(SHARPE_SURVIVORS_CSV),
            "sharpe_debug_report_txt": str(SHARPE_DEBUG_REPORT_TXT),
            "sports_alpha_json": str(SPORTS_ALPHA_JSON),
            "lumaq_report_json": str(LUMAQ_REPORT_JSON),
        },
        "summary": {
            "readiness_score_0_100": safe_float(report.get("readiness_score_0_100")),
            "overall_status": report.get("overall_status", "unknown"),
            "files_indexed": int(safe_float(report.get("summary", {}).get("files_indexed"), 0.0)),
            "open_micro_tasks": int(safe_float(report.get("summary", {}).get("open_micro_tasks"), 0.0)),
            "critical_micro_tasks": int(safe_float(report.get("summary", {}).get("critical_micro_tasks"), 0.0)),
            "mirror_sync_pct": safe_float(report.get("summary", {}).get("mirror_sync_pct")),
            "validated_true_sharpe_count": len(survivors),
            "debug_sharpe_candidates_count": len(debug_rows),
        },
        "institutional_top10_strategies": institutional,
        "trinity_top10_strategies": trinity,
        "true_sharpe_top10_validated": survivors,
        "true_sharpe_top10_debug_only": debug_rows[:10],
        "sports_alpha_top10": sports,
        "lumaq_blocker_top10": blockers,
        "prediction_market_note": {
            "primary_exchange": "Kalshi",
            "fit": "Use sports_alpha_top10 and macro/infra signal winners as contract watchlist seeds; map only to contracts with clear event resolution rules.",
            "guardrail": "Do not auto-submit real-money prediction market orders without separate key segregation, per-market risk caps, and legal/regional checks.",
        },
    }


def build_registry_markdown(registry: dict[str, Any]) -> str:
    summary = registry.get("summary", {})

    inst_rows = [
        [
            str(r.get("rank", "")),
            str(r.get("strategy", "")),
            str(r.get("algo", "")),
            f"{safe_float(r.get('test_sharpe')):.3f}",
            f"{safe_float(r.get('institutional_score')):.3f}",
        ]
        for r in registry.get("institutional_top10_strategies", [])
    ]
    tri_rows = [
        [
            str(r.get("rank", "")),
            str(r.get("family", "")),
            f"{safe_float(r.get('sharpe')):.3f}",
            f"{safe_float(r.get('score')):.3f}",
            f"{safe_float(r.get('max_dd')):.4f}",
        ]
        for r in registry.get("trinity_top10_strategies", [])
    ]
    true_rows = [
        [
            str(r.get("rank", "")),
            str(r.get("strategy", "")),
            str(r.get("pair", "")),
            f"{safe_float(r.get('mc_sharpe')):.3f}",
            f"{safe_float(r.get('sharpe')):.3f}",
        ]
        for r in registry.get("true_sharpe_top10_validated", [])
    ]
    debug_rows = [
        [
            str(i + 1),
            str(r.get("strategy", "")),
            str(r.get("pair", "")),
            f"{safe_float(r.get('sharpe')):.3f}",
            f"{safe_float(r.get('mc_sharpe')):.3f}",
        ]
        for i, r in enumerate(registry.get("true_sharpe_top10_debug_only", []))
    ]
    sports_rows = [
        [
            str(r.get("rank", "")),
            str(r.get("pick", "")),
            f"{safe_float(r.get('edge_pct')):.2f}%",
            f"{safe_float(r.get('alpha_score_v2')):.2f}",
            str(r.get("game", ""))[:52],
        ]
        for r in registry.get("sports_alpha_top10", [])
    ]
    blocker_rows = [
        [
            str(r.get("rank", "")),
            str(r.get("priority", "")),
            str(r.get("source", "")),
            str(r.get("task", ""))[:60],
        ]
        for r in registry.get("lumaq_blocker_top10", [])
    ]

    parts: list[str] = [
        "# LumaQ Top 10 Alpha Registry",
        "",
        f"Generated UTC: {registry.get('generated_utc', '-')}",
        f"Readiness: {safe_float(summary.get('readiness_score_0_100')):.2f} ({summary.get('overall_status', '-')})",
        f"Open micro tasks: {int(safe_float(summary.get('open_micro_tasks')))} | Critical: {int(safe_float(summary.get('critical_micro_tasks')))} | Mirror sync: {safe_float(summary.get('mirror_sync_pct')):.2f}%",
        "",
        "## Institutional Top 10 (Execution Stack)",
        md_table(["Rank", "Strategy", "Algo", "Test Sharpe", "Institutional Score"], inst_rows or [["-", "No data", "-", "-", "-"]]),
        "",
        "## Trinity Top 10 (High-Sharpe Candidates)",
        md_table(["Rank", "Family", "Sharpe", "Score", "Max DD"], tri_rows or [["-", "No data", "-", "-", "-"]]),
        "",
        "## True Sharpe Top 10 (Reality Validated)",
    ]

    if true_rows:
        parts.append(md_table(["Rank", "Strategy", "Pair", "MC Sharpe", "Raw Sharpe"], true_rows))
    else:
        parts.extend(
            [
                "No validated true-sharpe survivors currently passed the reality filter.",
                "",
                "### Debug Sharpe Candidates (Not Reality-Passed)",
                md_table(["Rank", "Strategy", "Pair", "Sharpe", "MC Sharpe"], debug_rows or [["-", "No debug rows", "-", "-", "-"]]),
            ]
        )

    parts.extend(
        [
            "",
            "## Sports/Prediction Alpha Top 10",
            md_table(["Rank", "Pick", "Edge", "Alpha v2", "Game"], sports_rows or [["-", "No data", "-", "-", "-"]]),
            "",
            "## LumaQ Blocker Top 10",
            md_table(["Rank", "Priority", "Source", "Task"], blocker_rows or [["-", "No blockers", "-", "-"]]),
        ]
    )

    return "\n".join(parts)


def build_stage_script(report: dict[str, Any], registry: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    readiness = safe_float(report.get("readiness_score_0_100"))
    open_tasks = int(safe_float(summary.get("open_micro_tasks"), 0.0))
    critical_tasks = int(safe_float(summary.get("critical_micro_tasks"), 0.0))
    mirror_sync = safe_float(summary.get("mirror_sync_pct"), 0.0)

    top_trinity = (registry.get("trinity_top10_strategies") or [{}])[0]
    top_inst = (registry.get("institutional_top10_strategies") or [{}])[0]
    top_sports = (registry.get("sports_alpha_top10") or [{}])[0]

    return f"""
# LumaQ 3-Minute Stage Script

Generated UTC: {now_utc()}

## 0:00-0:20 Opening
This is LumaQ, the command brain that unifies execution truth, alpha discovery, and investor narrative.
Current measured state is readiness {readiness:.0f}/100, status {report.get('overall_status', 'unknown').upper()}.

## 0:20-1:00 What Is Running Now
Micro agent is enforcing file-level runtime truth with {open_tasks} open tasks and {critical_tasks} critical blockers.
Meso agent tracks subsystem integrity and mirror parity; dashboard mirror sync is {mirror_sync:.2f}%.
Macro agent converts live telemetry into investor-grade narrative and hard-ask framing.

## 1:00-1:40 Proof Layer (Top 10 Signals)
Trinity high-sharpe candidate currently leads at sharpe {safe_float(top_trinity.get('sharpe')):.2f} in family {top_trinity.get('family', '-')}
Institutional execution stack lead strategy is {top_inst.get('strategy', '-')} with test sharpe {safe_float(top_inst.get('test_sharpe')):.2f}
Sports/prediction alpha lead is {top_sports.get('pick', '-')} with edge {safe_float(top_sports.get('edge_pct')):.2f}% and alpha-v2 {safe_float(top_sports.get('alpha_score_v2')):.2f}

## 1:40-2:20 Reality Guardrails
Validated true-sharpe list is separated from debug sharpe candidates.
If the reality filter has zero survivors, we say it clearly and route capital to validated lanes only.
No narrative is accepted without artifact-backed telemetry and hash-linked proof outputs.

## 2:20-3:00 Ask and Next Sprint
Fund a 90-day acceleration sprint to close critical blockers, lift mirror sync above 95%, and move from proof-rich paper workflows into controlled live deployment.
Immediate 5-day focus is to clear stale probes, close mirror drift, and run a daily top-10 alpha briefing with live risk gates.
"""


def build_burndown(report: dict[str, Any], registry: dict[str, Any]) -> str:
    tasks = report.get("micro_agent", {}).get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []

    critical = [t for t in tasks if isinstance(t, dict) and str(t.get("priority", "")).lower() == "critical"]
    stale_critical = [t for t in critical if str(t.get("source", "")) == "staleness"]
    mirror_critical = [t for t in critical if str(t.get("source", "")) == "mirror_drift"]
    remaining = [t for t in critical if t not in stale_critical and t not in mirror_critical]

    def task_lines(items: list[dict[str, Any]], default_text: str) -> str:
        if not items:
            return f"- [ ] {default_text}"
        lines = []
        for task in items:
            title = str(task.get("task", "untitled task"))
            target = str(task.get("target", "")).strip()
            if target:
                lines.append(f"- [ ] {title} ({target})")
            else:
                lines.append(f"- [ ] {title}")
        return "\n".join(lines)

    blocker_rows = registry.get("lumaq_blocker_top10", [])
    blocker_snapshot = "\n".join(
        f"- {row.get('priority', 'warn').upper()}: {row.get('task', '-')}"
        for row in blocker_rows[:5]
    ) or "- No blocker rows available"

    return f"""
# LumaQ 5-Day Blocker Burn-Down

Generated UTC: {now_utc()}

## Day 1 - Critical Freshness Recovery
{task_lines(stale_critical[:4], 'Refresh critical staleness probes from execution and performance feeds')}

Commands:
- powershell -ExecutionPolicy Bypass -File code/deploy/RUN_END_TO_END_STALENESS_FINDER.ps1
- powershell -ExecutionPolicy Bypass -File code/deploy/RUN_LUMAQ_BRAIN.ps1

Success artifacts:
- out/ops/staleness_report.json
- out/ops/lumaq_brain_report.json

## Day 2 - Critical Mirror Drift Closure
{task_lines(mirror_critical[:4], 'Resolve critical dashboard mirror drift files')}

Commands:
- powershell -ExecutionPolicy Bypass -File code/deploy/RUN_LUMAQ_BRAIN.ps1
- c:/LumaTrader/venv3.11/Scripts/python.exe code/execution/build_top_strategy_baseline.py

Success artifacts:
- out/ops/lumaq_brain_report.json
- out/execution/top_system_strategy_baseline.json

## Day 3 - Live Execution Safety + Proof
{task_lines(remaining[:4], 'Verify controller/heartbeat and remove remaining critical blockers')}

Commands:
- powershell -ExecutionPolicy Bypass -File code/RUN_KRAKEN_STAGE2_WITH_ENV.ps1
- c:/LumaTrader/venv3.11/Scripts/python.exe code/build_kraken_positive_proof.py

Success artifacts:
- out/execution/kraken_positive_proof.json
- out/execution/vps_growth_controller_status.json

## Day 4 - Top 10 Command Intelligence
- [ ] Regenerate consolidated top-10 alpha board for trading, sports, and sharp validation lanes
- [ ] Publish top-10 briefing in command room before demo dry run

Commands:
- c:/LumaTrader/venv3.11/Scripts/python.exe code/deploy/build_lumaq_execution_pack.py
- powershell -Command "curl.exe -sS http://127.0.0.1:8787/api/ops/lumaq"

Success artifacts:
- out/ops/lumaq_top10_alpha_registry.json
- out/ops/lumaq_top10_alpha_registry.md

## Day 5 - Demo Freeze + Submission Pack
- [ ] Freeze final dashboard state and investor talk track
- [ ] Final grants packet review with latest metrics
- [ ] Run one full command-center smoke check before presentation

Commands:
- powershell -ExecutionPolicy Bypass -File code/deploy/RUN_LUMAQ_BRAIN.ps1
- c:/LumaTrader/venv3.11/Scripts/python.exe code/execution/build_top_strategy_baseline.py

Success artifacts:
- out/ops/lumaq_investor_talk_track.md
- out/institutional_grant_proposals.json

## Live Blocker Snapshot
{blocker_snapshot}
"""


def main() -> int:
    report = read_json(LUMAQ_REPORT_JSON, {})
    if not isinstance(report, dict) or not report:
        raise FileNotFoundError(f"Missing or invalid LumaQ report: {LUMAQ_REPORT_JSON}")

    registry = build_registry(report)
    registry_md = build_registry_markdown(registry)
    stage_script = build_stage_script(report, registry)
    burndown = build_burndown(report, registry)

    write_json(TOP10_REGISTRY_JSON, registry)
    write_text(TOP10_REGISTRY_MD, registry_md)
    write_text(STAGE_SCRIPT_MD, stage_script)
    write_text(BURNDOWN_MD, burndown)

    print(f"[LUMAQ_EXEC_PACK] wrote {TOP10_REGISTRY_JSON}")
    print(f"[LUMAQ_EXEC_PACK] wrote {TOP10_REGISTRY_MD}")
    print(f"[LUMAQ_EXEC_PACK] wrote {STAGE_SCRIPT_MD}")
    print(f"[LUMAQ_EXEC_PACK] wrote {BURNDOWN_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
