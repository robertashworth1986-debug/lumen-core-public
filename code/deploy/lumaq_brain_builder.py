from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = ROOT.parent
OUT_DIR = ROOT / "out" / "ops"

REPORT_JSON = OUT_DIR / "lumaq_brain_report.json"
REPORT_MD = OUT_DIR / "lumaq_brain_report.md"
TALK_TRACK_MD = OUT_DIR / "lumaq_investor_talk_track.md"

STALENESS_REPORT_FILE = OUT_DIR / "staleness_report.json"
OPPORTUNITY_BRIEF_FILE = ROOT / "out" / "execution" / "institutional_opportunity_executive_brief.json"
SCORECARD_FILE = ROOT / "out" / "execution" / "investor_proof_scorecard.json"
PACKAGE_AUDIT_FILE = ROOT / "out" / "execution" / "package_leverage_audit.json"

STACK_DASHBOARD = ROOT / "dashboard"
TOP_DASHBOARD = WORKSPACE_ROOT / "dashboard"

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "venv3.11",
    "__pycache__",
    "node_modules",
    "archive",
    "archives",
    "out",
}

CRITICAL_MIRROR_FILES = {
    "quant_lab.html",
    "mission_control.html",
    "staleness_command_center.html",
    "luma_experience.html",
    "scenario_mission.html",
    "investor_command_room.html",
    "investor_wallboard.html",
    "grants.html",
    "kraken_execution_dashboard.html",
}

SYSTEM_DEFINITIONS: list[tuple[str, str, tuple[str, ...], str]] = [
    (
        "execution_runtime",
        "Execution Runtime",
        (
            "execution",
            "executor",
            "orchestrator",
            "live_executor",
            "trade",
            "kraken",
            "alpaca",
            "supervisor",
        ),
        "Keep trading loops alive and writing fresh proof artifacts.",
    ),
    (
        "proof_audit",
        "Proof And Audit",
        (
            "proof",
            "audit",
            "ledger",
            "sha256",
            "frozen",
            "validation",
            "evidence",
        ),
        "Guarantee claims are auditable with deterministic artifact trails.",
    ),
    (
        "investor_surface",
        "Investor Surface",
        (
            "dashboard",
            "mission_control",
            "quant_lab",
            "wallboard",
            "investor",
            "experience",
        ),
        "Render explainable, demo-ready outputs with no blind spots.",
    ),
    (
        "deployment_ops",
        "Deployment Ops",
        (
            "deploy",
            ".ps1",
            "bootstrap",
            "startup",
            "readiness",
            "checklist",
        ),
        "Arm launch, restart, and guardrail procedures for operator control.",
    ),
    (
        "intelligence_models",
        "Intelligence Models",
        (
            "forecast",
            "anomaly",
            "router",
            "harmonic",
            "model",
            "ml",
            "alpha",
            "scout",
        ),
        "Generate signal quality and explainable decision intelligence.",
    ),
    (
        "growth_and_grants",
        "Growth And Grants",
        (
            "grant",
            "federal",
            "sbir",
            "pitch",
            "proposal",
            "business",
            "funding",
        ),
        "Translate engineering capability into revenue and non-dilutive funding.",
    ),
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def fmt_usd(value: float) -> str:
    return f"${value:,.0f}"


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _iter_files(base: Path, max_files: int) -> list[Path]:
    out: list[Path] = []
    if not base.exists():
        return out

    for path in base.rglob("*"):
        if len(out) >= max_files:
            break
        if path.is_dir():
            continue
        rel_parts = {p.lower() for p in path.relative_to(base).parts}
        if rel_parts.intersection(SKIP_DIR_NAMES):
            continue
        out.append(path)
    return out


def _classify_system(rel_path: str) -> str:
    rel_lower = rel_path.lower()
    for system_id, _, keywords, _ in SYSTEM_DEFINITIONS:
        if any(token in rel_lower for token in keywords):
            return system_id
    return "foundation"


def scan_lumaq_surface(max_files: int) -> dict[str, Any]:
    roots = [ROOT / "code", ROOT / "dashboard", ROOT / "config", TOP_DASHBOARD]
    scanned: list[Path] = []
    capped = False
    per_root_budget = max(1, max_files // max(1, len(roots)))

    for base in roots:
        files = _iter_files(base, per_root_budget)
        scanned.extend(files)
        if len(files) >= per_root_budget:
            capped = True

    # Deduplicate while preserving order.
    seen: set[str] = set()
    uniq: list[Path] = []
    for path in scanned:
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(path)

    if len(uniq) > max_files:
        uniq = uniq[:max_files]
        capped = True

    ext_counter: Counter[str] = Counter()
    system_counter: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    newest: dict[str, datetime] = {}
    recent_rows: list[tuple[datetime, str]] = []

    for path in uniq:
        rel = path.relative_to(WORKSPACE_ROOT).as_posix() if path.is_absolute() else str(path)
        ext = path.suffix.lower() or "(none)"
        ext_counter[ext] += 1

        system_id = _classify_system(rel)
        system_counter[system_id] += 1

        bucket = samples.setdefault(system_id, [])
        if len(bucket) < 6:
            bucket.append(rel)

        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            prev = newest.get(system_id)
            if prev is None or mtime > prev:
                newest[system_id] = mtime
            recent_rows.append((mtime, rel))
        except Exception:
            continue

    recent_rows.sort(key=lambda row: row[0], reverse=True)
    recent_files = [
        {"path": rel, "mtime_utc": iso_utc(mtime)}
        for mtime, rel in recent_rows[:20]
    ]

    system_map: dict[str, dict[str, Any]] = {}
    for system_id, _, _, mission in SYSTEM_DEFINITIONS:
        system_map[system_id] = {
            "file_count": int(system_counter.get(system_id, 0)),
            "mission": mission,
            "sample_files": samples.get(system_id, []),
            "newest_update_utc": iso_utc(newest.get(system_id)),
        }
    system_map["foundation"] = {
        "file_count": int(system_counter.get("foundation", 0)),
        "mission": "Host shared utilities and baseline components across agents.",
        "sample_files": samples.get("foundation", []),
        "newest_update_utc": iso_utc(newest.get("foundation")),
    }

    return {
        "files_indexed": len(uniq),
        "scan_capped": bool(capped),
        "extension_counts": dict(ext_counter.most_common(20)),
        "system_counts": dict(system_counter),
        "systems": system_map,
        "recent_files": recent_files,
    }


def _build_dashboard_html_map(base: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    if not base.exists():
        return out
    for html in base.rglob("*.html"):
        rel = html.relative_to(base).as_posix().lower()
        out[rel] = html
    return out


def analyze_mirror_drift() -> dict[str, Any]:
    stack_map = _build_dashboard_html_map(STACK_DASHBOARD)
    top_map = _build_dashboard_html_map(TOP_DASHBOARD)
    all_keys = sorted(set(stack_map.keys()) | set(top_map.keys()))

    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    critical_issues = 0

    for key in all_keys:
        stack_path = stack_map.get(key)
        top_path = top_map.get(key)
        base_name = Path(key).name.lower()

        if stack_path is None:
            status = "missing_in_stack"
            severity = "critical" if base_name in CRITICAL_MIRROR_FILES else "warn"
        elif top_path is None:
            status = "missing_in_top"
            severity = "critical" if base_name in CRITICAL_MIRROR_FILES else "warn"
        else:
            try:
                status = "synced" if sha256_file(stack_path) == sha256_file(top_path) else "hash_mismatch"
            except Exception:
                status = "hash_mismatch"
            severity = "info" if status == "synced" else ("critical" if base_name in CRITICAL_MIRROR_FILES else "warn")

        if severity == "critical" and status != "synced":
            critical_issues += 1

        counts[status] += 1
        rows.append(
            {
                "relative_path": key,
                "status": status,
                "severity": severity,
                "stack_path": str(stack_path) if stack_path else "",
                "top_path": str(top_path) if top_path else "",
            }
        )

    synced = counts.get("synced", 0)
    total = max(1, len(all_keys))
    sync_pct = round((float(synced) / float(total)) * 100.0, 2)

    rows.sort(
        key=lambda r: (
            0 if r["severity"] == "critical" else 1 if r["severity"] == "warn" else 2,
            r["relative_path"],
        )
    )

    return {
        "stack_dashboard_dir": str(STACK_DASHBOARD),
        "top_dashboard_dir": str(TOP_DASHBOARD),
        "summary": {
            "total_html_assets": len(all_keys),
            "synced": synced,
            "missing_in_stack": counts.get("missing_in_stack", 0),
            "missing_in_top": counts.get("missing_in_top", 0),
            "hash_mismatch": counts.get("hash_mismatch", 0),
            "sync_pct": sync_pct,
            "critical_issues": critical_issues,
        },
        "drift_rows": rows[:200],
    }


def build_micro_tasks(staleness_report: dict[str, Any], mirror: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []

    blockers = staleness_report.get("blockers", []) if isinstance(staleness_report, dict) else []
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        tasks.append(
            {
                "source": "staleness",
                "priority": blocker.get("severity", "critical"),
                "task": f"Refresh stale critical probe: {blocker.get('id', 'unknown')}",
                "status": "open",
                "detail": blocker.get("notes", ""),
                "target": blocker.get("target", ""),
            }
        )

    probes = staleness_report.get("probes", []) if isinstance(staleness_report, dict) else []
    for probe in probes:
        if not isinstance(probe, dict):
            continue
        if str(probe.get("status", "")).lower() not in {"stale", "missing", "error", "broken"}:
            continue
        if len(tasks) >= 25:
            break
        tasks.append(
            {
                "source": "staleness",
                "priority": probe.get("severity", "warn"),
                "task": f"Repair {probe.get('status', 'issue')} probe: {probe.get('id', 'unknown')}",
                "status": "open",
                "detail": probe.get("hint", ""),
                "target": probe.get("target", ""),
            }
        )

    drift_rows = mirror.get("drift_rows", []) if isinstance(mirror, dict) else []
    for row in drift_rows:
        if not isinstance(row, dict):
            continue
        if row.get("status") == "synced":
            continue
        if len(tasks) >= 40:
            break
        tasks.append(
            {
                "source": "mirror_drift",
                "priority": row.get("severity", "warn"),
                "task": f"Resolve dashboard mirror drift: {row.get('relative_path', '')}",
                "status": "open",
                "detail": f"state={row.get('status', 'unknown')}",
                "target": row.get("relative_path", ""),
            }
        )

    priority_order = {"critical": 0, "warn": 1, "info": 2}
    tasks.sort(key=lambda t: (priority_order.get(str(t.get("priority", "warn")), 5), str(t.get("task", ""))))
    return tasks


def build_meso_summary(scan: dict[str, Any]) -> list[dict[str, Any]]:
    system_counts = scan.get("systems", {}) if isinstance(scan, dict) else {}
    rows: list[dict[str, Any]] = []

    display_map = {sid: name for sid, name, _, _ in SYSTEM_DEFINITIONS}
    display_map["foundation"] = "Foundation"

    for system_id, meta in system_counts.items():
        if not isinstance(meta, dict):
            continue
        rows.append(
            {
                "id": system_id,
                "name": display_map.get(system_id, system_id.replace("_", " ").title()),
                "file_count": safe_int(meta.get("file_count", 0)),
                "mission": str(meta.get("mission", "")),
                "newest_update_utc": str(meta.get("newest_update_utc", "")),
                "sample_files": list(meta.get("sample_files", []))[:4],
            }
        )

    rows.sort(key=lambda r: int(r.get("file_count", 0)), reverse=True)
    return rows


def build_macro_narrative(
    staleness_report: dict[str, Any],
    mirror: dict[str, Any],
    opportunity: dict[str, Any],
    scorecard: dict[str, Any],
    package_audit: dict[str, Any],
) -> dict[str, Any]:
    measured_hour = safe_float(opportunity.get("measured_total_hour_usd", 0.0))
    rolling_hour = safe_float(opportunity.get("rolling_total_hour_usd", 0.0))
    top_sector = str(opportunity.get("top_sector", "multi_sector") or "multi_sector")

    paper_equity = safe_float(scorecard.get("current_equity_usd", 0.0))
    closed_trades = safe_int(scorecard.get("closed_trades", 0))

    active_util_pct = safe_float(package_audit.get("active_utilization_pct", 0.0))

    blocker_count = len(staleness_report.get("blockers", [])) if isinstance(staleness_report, dict) else 0
    mirror_crit = safe_int(((mirror.get("summary", {}) or {}).get("critical_issues", 0)))

    what_we_sell = (
        "LumaQ is an engineering-first command system that converts noisy multi-domain data into "
        "actionable, auditable decisions across trading, infrastructure, and investor operations."
    )

    why_now = (
        f"The current measured opportunity surface is {fmt_usd(measured_hour)}/hour (rolling {fmt_usd(rolling_hour)}/hour) "
        f"with {top_sector} leading, which means this is already an active intelligence surface, not a concept deck."
    )

    moat = (
        "The moat is operational truth: chain-of-custody artifacts, health gates, and replayable proofs that reduce "
        "storytelling risk while increasing decision velocity."
    )

    investors_see = [
        f"Proof discipline: {blocker_count} open staleness blocker(s) and explicit remediation paths.",
        f"Surface consistency: dashboard mirror critical drift count {mirror_crit}.",
        f"Engineering depth: package active utilization {active_util_pct:.1f}% across the stack.",
        f"Execution telemetry: paper equity snapshot {fmt_usd(paper_equity)} with {closed_trades} closed trades tracked.",
    ]

    one_minute_pitch = (
        "LumaQ is the operating system for high-stakes decision environments. "
        "It runs three linked agent layers: Micro protects freshness and mirror integrity, "
        "Meso manages subsystem health and synthesis, and Macro turns verified telemetry into investor-ready narrative. "
        "You are funding acceleration of a live, instrumented system with measurable opportunity and audit-grade controls."
    )

    hard_ask = (
        "Fund a 90-day scale sprint to increase measured-lane coverage, tighten live execution freshness, "
        "and convert proof-rich paper workflows into controlled production milestones."
    )

    return {
        "what_we_sell": what_we_sell,
        "why_now": why_now,
        "moat": moat,
        "what_investors_want_to_see": investors_see,
        "one_minute_pitch": one_minute_pitch,
        "hard_ask": hard_ask,
    }


def build_llm_strategy() -> dict[str, Any]:
    return {
        "recommended_path": "RAG-first, not full model retraining in the 5-day window",
        "reason": [
            "Your data changes constantly, so frozen model weights age too fast.",
            "RAG over local artifacts is cheaper, faster, and auditable.",
            "Three-agent orchestration gives role separation without three model-training projects.",
        ],
        "micro_agent": {
            "goal": "File-level truth and readiness enforcement",
            "cadence": "every 5 minutes",
            "inputs": [
                "out/ops/staleness_report.json",
                "dashboard mirror drift scan",
                "execution_events.jsonl freshness",
            ],
            "outputs": [
                "open blockers list",
                "autofix queue",
                "go/no-go readiness flag",
            ],
        },
        "meso_agent": {
            "goal": "Subsystem synthesis and dependency awareness",
            "cadence": "every 30 minutes",
            "inputs": [
                "code and dashboard file index",
                "ops reports",
                "proof-pack manifests",
            ],
            "outputs": [
                "module health map",
                "critical path alerts",
                "deployment notes",
            ],
        },
        "macro_agent": {
            "goal": "Investor-grade narrative from live telemetry",
            "cadence": "on-demand and pre-demo",
            "inputs": [
                "institutional opportunity brief",
                "proof scorecards",
                "micro and meso output summaries",
            ],
            "outputs": [
                "one-minute pitch",
                "objection handling notes",
                "capital ask framing",
            ],
        },
    }


def calc_readiness_score(staleness_report: dict[str, Any], mirror: dict[str, Any], micro_tasks: list[dict[str, Any]]) -> int:
    score = 100

    blockers = len(staleness_report.get("blockers", [])) if isinstance(staleness_report, dict) else 0
    score -= min(60, blockers * 25)

    mirror_critical = safe_int(((mirror.get("summary", {}) or {}).get("critical_issues", 0)))
    score -= min(30, mirror_critical * 10)

    total_open = len([t for t in micro_tasks if str(t.get("status", "open")) == "open"])
    score -= min(20, total_open // 6)

    if not isinstance(staleness_report, dict) or not staleness_report:
        score -= 10

    return max(0, min(100, int(score)))


def overall_status(micro_tasks: list[dict[str, Any]]) -> str:
    critical_open = [t for t in micro_tasks if str(t.get("priority", "")).lower() == "critical"]
    warn_open = [t for t in micro_tasks if str(t.get("priority", "")).lower() == "warn"]
    if critical_open:
        return "critical"
    if warn_open:
        return "warn"
    return "ok"


def build_report(max_files: int) -> dict[str, Any]:
    staleness = load_json(STALENESS_REPORT_FILE, {})
    opportunity = load_json(OPPORTUNITY_BRIEF_FILE, {})
    scorecard = load_json(SCORECARD_FILE, {})
    package_audit = load_json(PACKAGE_AUDIT_FILE, {})

    scan = scan_lumaq_surface(max_files=max_files)
    mirror = analyze_mirror_drift()
    micro_tasks = build_micro_tasks(staleness, mirror)
    meso_systems = build_meso_summary(scan)
    macro = build_macro_narrative(staleness, mirror, opportunity, scorecard, package_audit)
    strategy = build_llm_strategy()

    status = overall_status(micro_tasks)
    readiness = calc_readiness_score(staleness, mirror, micro_tasks)

    return {
        "schema": "lumaq_micro_meso_macro_brain_v1",
        "generated_utc": iso_utc(now_utc()),
        "workspace_root": str(WORKSPACE_ROOT),
        "stack_root": str(ROOT),
        "overall_status": status,
        "readiness_score_0_100": readiness,
        "summary": {
            "files_indexed": safe_int(scan.get("files_indexed", 0)),
            "scan_capped": bool(scan.get("scan_capped", False)),
            "open_micro_tasks": len(micro_tasks),
            "critical_micro_tasks": len([t for t in micro_tasks if str(t.get("priority", "")).lower() == "critical"]),
            "mirror_sync_pct": safe_float(((mirror.get("summary", {}) or {}).get("sync_pct", 0.0))),
        },
        "llm_strategy": strategy,
        "micro_agent": {
            "mission": "Continuously prevent stale, broken, and unsynced surfaces.",
            "tasks": micro_tasks[:40],
            "staleness_report_path": str(STALENESS_REPORT_FILE),
            "mirror": mirror,
        },
        "meso_agent": {
            "mission": "Own subsystem health and surface cross-module risk early.",
            "scan": scan,
            "systems": meso_systems,
        },
        "macro_agent": {
            "mission": "Translate verified engineering telemetry into undeniable investor narrative.",
            "narrative": macro,
        },
        "source_artifacts": {
            "staleness": str(STALENESS_REPORT_FILE),
            "opportunity_brief": str(OPPORTUNITY_BRIEF_FILE),
            "investor_scorecard": str(SCORECARD_FILE),
            "package_audit": str(PACKAGE_AUDIT_FILE),
        },
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# LumaQ Brain Report")
    lines.append("")
    lines.append(f"Generated UTC: {report.get('generated_utc', '')}")
    lines.append(f"Overall status: {report.get('overall_status', 'unknown')}")
    lines.append(f"Readiness score: {report.get('readiness_score_0_100', 0)}/100")
    lines.append("")

    summary = report.get("summary", {}) or {}
    lines.append("## Snapshot")
    lines.append(f"- Files indexed: {summary.get('files_indexed', 0)}")
    lines.append(f"- Open micro tasks: {summary.get('open_micro_tasks', 0)}")
    lines.append(f"- Critical micro tasks: {summary.get('critical_micro_tasks', 0)}")
    lines.append(f"- Dashboard mirror sync: {summary.get('mirror_sync_pct', 0.0)}%")
    lines.append("")

    lines.append("## LLM Strategy")
    llm_strategy = report.get("llm_strategy", {}) or {}
    lines.append(f"- Recommended path: {llm_strategy.get('recommended_path', '')}")
    for reason in llm_strategy.get("reason", []) or []:
        lines.append(f"- Why: {reason}")
    lines.append("")

    lines.append("## Micro Agent Tasks")
    lines.append("| Priority | Task | Source | Detail |")
    lines.append("| --- | --- | --- | --- |")
    for task in (report.get("micro_agent", {}) or {}).get("tasks", [])[:20]:
        lines.append(
            "| {priority} | {task} | {source} | {detail} |".format(
                priority=str(task.get("priority", "warn")).upper(),
                task=str(task.get("task", "")).replace("|", "/"),
                source=str(task.get("source", "")).replace("|", "/"),
                detail=str(task.get("detail", "")).replace("|", "/"),
            )
        )
    lines.append("")

    lines.append("## Meso Agent Systems")
    for system in (report.get("meso_agent", {}) or {}).get("systems", [])[:8]:
        lines.append(f"### {system.get('name', 'System')} ({system.get('file_count', 0)} files)")
        lines.append(f"- Mission: {system.get('mission', '')}")
        lines.append(f"- Newest update: {system.get('newest_update_utc', '')}")
        samples = system.get("sample_files", []) or []
        if samples:
            lines.append("- Sample files:")
            for path in samples:
                lines.append(f"  - {path}")
        lines.append("")

    narrative = ((report.get("macro_agent", {}) or {}).get("narrative", {}) or {})
    lines.append("## Macro Narrative")
    lines.append(f"- What we sell: {narrative.get('what_we_sell', '')}")
    lines.append(f"- Why now: {narrative.get('why_now', '')}")
    lines.append(f"- Moat: {narrative.get('moat', '')}")
    lines.append("- What investors want to see:")
    for item in narrative.get("what_investors_want_to_see", []) or []:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append("## One-Minute Pitch")
    lines.append(narrative.get("one_minute_pitch", ""))
    lines.append("")
    lines.append("## Hard Ask")
    lines.append(narrative.get("hard_ask", ""))
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_talk_track(report: dict[str, Any]) -> str:
    narrative = ((report.get("macro_agent", {}) or {}).get("narrative", {}) or {})
    summary = report.get("summary", {}) or {}
    lines = [
        "# LumaQ Demo Day Talk Track",
        "",
        "## 20-second open",
        "- LumaQ is an engineering command system that keeps decision intelligence, execution proof, and investor narrative in one loop.",
        f"- Readiness right now is {report.get('readiness_score_0_100', 0)}/100 with status {str(report.get('overall_status', 'unknown')).upper()}.",
        "",
        "## 45-second proof",
        f"- Micro layer is tracking {summary.get('open_micro_tasks', 0)} open actions and {summary.get('critical_micro_tasks', 0)} critical blockers.",
        f"- Dashboard mirror sync is {summary.get('mirror_sync_pct', 0.0)}%, so we can prove parity across demo surfaces.",
        "- Every claim is tied to generated artifacts, not memory or improvised screenshots.",
        "",
        "## 60-second investor close",
        f"- {narrative.get('what_we_sell', '')}",
        f"- {narrative.get('why_now', '')}",
        f"- {narrative.get('hard_ask', '')}",
        "",
        f"Generated UTC: {report.get('generated_utc', '')}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(report: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    REPORT_MD.write_text(to_markdown(report), encoding="utf-8")
    TALK_TRACK_MD.write_text(build_talk_track(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build LumaQ micro/meso/macro explainer artifacts.")
    parser.add_argument("--max-files", type=int, default=50000, help="Maximum files to index across code and dashboard surfaces.")
    parser.add_argument("--print-json", action="store_true", help="Print report JSON to stdout.")
    parser.add_argument("--fail-on-critical", action="store_true", help="Return exit code 2 when critical micro tasks remain open.")
    args = parser.parse_args()

    report = build_report(max_files=max(1000, int(args.max_files)))
    write_outputs(report)

    if args.print_json:
        print(json.dumps(report, indent=2))
    else:
        print(str(REPORT_JSON))
        print(str(REPORT_MD))
        print(str(TALK_TRACK_MD))

    critical_open = int((report.get("summary", {}) or {}).get("critical_micro_tasks", 0))
    if args.fail_on_critical and critical_open > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())