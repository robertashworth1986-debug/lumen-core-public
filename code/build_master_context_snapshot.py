from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
DASH = ROOT / "dashboard"

SNAPSHOT_JSON = EXEC_OUT / "master_context_snapshot.json"
SNAPSHOT_MD = EXEC_OUT / "master_context_snapshot.md"
RESUME_PROMPT_TXT = EXEC_OUT / "copilot_resume_prompt.txt"
PACKAGE_INVENTORY_JSON = EXEC_OUT / "python_package_inventory.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def read_jsonl_last(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
        if not lines:
            return default
        return json.loads(lines[-1])
    except Exception:
        return default


def pick_first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def pick_first_glob(glob_patterns: list[str]) -> Path | None:
    for pattern in glob_patterns:
        matches = sorted(ROOT.glob(pattern))
        if matches:
            return matches[0]
    return None


def rel(path: Path | None) -> str:
    if path is None:
        return "n/a"
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _package_inventory() -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    try:
        for dist in metadata.distributions():
            name = dist.metadata.get("Name") or dist.metadata.get("Summary") or "unknown"
            version = dist.version or "unknown"
            rows.append({"name": str(name), "version": str(version)})
    except Exception:
        rows = []

    rows.sort(key=lambda item: item.get("name", "").lower())
    focused = [
        "panel",
        "plotly",
        "pandas",
        "numpy",
        "cvxpy",
        "arch",
        "river",
        "fastapi",
        "uvicorn",
        "alpaca-py",
        "ccxt",
    ]
    focused_map: dict[str, str] = {}
    for pkg in focused:
        match = next((r for r in rows if r.get("name", "").lower() == pkg.lower()), None)
        focused_map[pkg] = match.get("version", "not_installed") if match else "not_installed"

    payload = {
        "generated_utc": now_utc(),
        "python_version": platform.python_version(),
        "package_count": len(rows),
        "focused_packages": focused_map,
        "packages": rows,
    }
    PACKAGE_INVENTORY_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build_snapshot() -> dict[str, Any]:
    package_inventory = _package_inventory()

    report_path = pick_first_existing([EXEC_OUT / "institutional_crypto_paper_report.json"])
    hash_path = pick_first_existing([EXEC_OUT / "institutional_crypto_paper_report_sha256.json"])
    heartbeat_path = pick_first_existing([EXEC_OUT / "institutional_crypto_dashboard_heartbeat.json"])

    health_latest_path = pick_first_existing(
        [
            EXEC_OUT / "institutional_crypto_dashboard_health_latest.json",
            EXEC_OUT / "institutional_crypto_dashboard_health_latest_test.json",
        ]
    )
    health_history_path = pick_first_existing(
        [
            EXEC_OUT / "institutional_crypto_dashboard_health_history.jsonl",
            EXEC_OUT / "institutional_crypto_dashboard_health_history_test.jsonl",
        ]
    )

    opportunity_history_path = pick_first_existing([EXEC_OUT / "institutional_sector_opportunity_history.jsonl"])
    regime_history_path = pick_first_existing([EXEC_OUT / "institutional_crypto_regime_history.jsonl"])
    ticker_status_path = pick_first_existing([EXEC_OUT / "multi_exchange_paper_ticker_status.json"])
    institutional_scorecard_path = pick_first_existing([EXEC_OUT / "institutional_metrics_scorecard.json"])

    sector_matrix_path = pick_first_existing([OUT / "sector_value_matrix.json"])
    source_truth_path = pick_first_existing([OUT / "source_truth_table.json"])
    frozen_deltas_path = pick_first_existing([OUT / "infra_frozen_deltas.jsonl"])

    unified_infra_dashboard_path = pick_first_existing([DASH / "infra_institutional_live_dashboard.html"])
    institutional_dashboard_path = pick_first_existing([DASH / "institutional_crypto_paper_dashboard.html"])

    autopilot_runner_path = pick_first_existing([CODE / "RUN_ZERO_TOUCH_AUTOPILOT.ps1"])
    ticker_runner_path = pick_first_existing([CODE / "RUN_MULTI_EXCHANGE_PAPER_TICKER.ps1"])
    dashboard_runner_path = pick_first_existing([CODE / "RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1"])
    dashboard_healthcheck_runner_path = pick_first_existing([CODE / "RUN_INSTITUTIONAL_DASHBOARD_HEALTHCHECK.ps1"])

    report = read_json(report_path, {})
    portfolio = report.get("portfolio", {}) if isinstance(report, dict) else {}
    audit = report.get("decision_audit", {}) if isinstance(report, dict) else {}
    allocator = audit.get("scientific_allocator", {}) if isinstance(audit, dict) else {}
    regime = audit.get("regime_controller", {}) if isinstance(audit, dict) else {}

    heartbeat = read_json(heartbeat_path, {})
    health_latest = read_json(health_latest_path, {})
    health_last = read_jsonl_last(health_history_path, {})
    opportunity_last = read_jsonl_last(opportunity_history_path, {})
    regime_last = read_jsonl_last(regime_history_path, {})
    ticker_status = read_json(ticker_status_path, {})

    summary = {
        "generated_utc": now_utc(),
        "workspace_root": rel(ROOT),
        "objective": "Recover full operational context quickly after chat/session disconnect and resume building without losing continuity.",
        "headline": {
            "mode": report.get("mode", "n/a"),
            "profile": report.get("profile", "n/a"),
            "equity_usd": portfolio.get("equity_usd", "n/a"),
            "cash_usd": portfolio.get("cash_usd", "n/a"),
            "return_pct": portfolio.get("return_pct", "n/a"),
            "positions_open": portfolio.get("positions_open", "n/a"),
            "regime": audit.get("regime", regime.get("regime", "n/a")),
            "allocator_status": allocator.get("optimizer_status", "n/a"),
            "allocator_solver": allocator.get("optimizer_solver", "n/a"),
        },
        "dashboard_health": {
            "heartbeat": heartbeat,
            "health_latest": health_latest,
            "health_last_history_entry": health_last,
        },
        "opportunity_rollup": {
            "last_snapshot": opportunity_last,
            "last_regime_snapshot": regime_last,
        },
        "artifact_paths": {
            "report": rel(report_path),
            "report_hash": rel(hash_path),
            "ticker_status": rel(ticker_status_path),
            "heartbeat": rel(heartbeat_path),
            "health_latest": rel(health_latest_path),
            "health_history": rel(health_history_path),
            "opportunity_history": rel(opportunity_history_path),
            "regime_history": rel(regime_history_path),
            "sector_matrix": rel(sector_matrix_path),
            "source_truth": rel(source_truth_path),
            "frozen_deltas": rel(frozen_deltas_path),
            "institutional_dashboard": rel(institutional_dashboard_path),
            "infra_dashboard": rel(unified_infra_dashboard_path),
            "python_package_inventory": rel(PACKAGE_INVENTORY_JSON),
            "institutional_metrics_scorecard": rel(institutional_scorecard_path),
        },
        "runner_paths": {
            "autopilot": rel(autopilot_runner_path),
            "ticker": rel(ticker_runner_path),
            "dashboard": rel(dashboard_runner_path),
            "dashboard_healthcheck": rel(dashboard_healthcheck_runner_path),
        },
        "restart_commands": {
            "reconnect_one_button": "powershell -ExecutionPolicy Bypass -File code/RUN_ONE_BUTTON_RECONNECT.ps1 -OpenResumePrompt",
            "reconnect_killall_autopilot": "powershell -ExecutionPolicy Bypass -File code/RUN_ONE_BUTTON_RECONNECT.ps1 -KillAllAndStartAutopilot -OpenResumePrompt",
            "reconnect_with_elite_optimizer": "powershell -ExecutionPolicy Bypass -File code/RUN_ONE_BUTTON_RECONNECT.ps1 -ForceNormalize -RunEliteOptimizer -OpenResumePrompt",
            "elite_optimizer": "powershell -ExecutionPolicy Bypass -File code/RUN_ELITE_STACK_OPTIMIZER.ps1",
            "institutional_scorecard": "c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/BUILD_INSTITUTIONAL_METRICS_SCORECARD.py",
            "ticker_detached": "powershell -ExecutionPolicy Bypass -File code/RUN_MULTI_EXCHANGE_PAPER_TICKER.ps1 -Institutional -Detach",
            "dashboard_serve_detached": "powershell -ExecutionPolicy Bypass -File code/RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1 -Mode serve -BindHost 127.0.0.1 -Port 5016 -RefreshSeconds 15 -Detach",
            "autopilot_loop": "powershell -ExecutionPolicy Bypass -File code/RUN_ZERO_TOUCH_AUTOPILOT.ps1",
            "dashboard_export": "c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/build_institutional_crypto_paper_dashboard.py --mode export",
            "snapshot_refresh": "c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/build_master_context_snapshot.py",
        },
        "moonshot_questions_to_ask_next": [
            "What are the top 3 measured sectors by rolling $/hr gain, and what exact telemetry is required to move each lane from MEDIUM to HIGH confidence?",
            "What failure classes can still create false-positive health, and how do we add artifact-based guardrails for each class?",
            "How do we separate realized value, measured proxy value, and modeled translation in investor output so claims stay audit-safe?",
            "Which one-page executive board should be generated every cycle for grants/pilots: KPI, chain-of-custody, and anomaly-to-dollar attribution?",
            "What is the minimum live TXID-backed milestone plan to transition from paper proof to controlled live capital deployment?",
        ],
        "notes": {
            "ticker_running_hint": ticker_status.get("status", "unknown") if isinstance(ticker_status, dict) else "unknown",
            "context_file_usage": "Paste out/execution/copilot_resume_prompt.txt into a new chat to quickly restore continuity.",
            "python_package_count": package_inventory.get("package_count", 0),
            "focused_packages": package_inventory.get("focused_packages", {}),
        },
    }
    return summary


def as_markdown(snapshot: dict[str, Any]) -> str:
    headline = snapshot.get("headline", {})
    artifacts = snapshot.get("artifact_paths", {})
    runners = snapshot.get("runner_paths", {})
    restart = snapshot.get("restart_commands", {})
    moonshot = snapshot.get("moonshot_questions_to_ask_next", [])

    lines = []
    lines.append("# Master Context Snapshot")
    lines.append("")
    lines.append(f"Generated UTC: {snapshot.get('generated_utc', 'n/a')}")
    lines.append("")
    lines.append("## Headline")
    lines.append(f"- Mode: {headline.get('mode', 'n/a')}")
    lines.append(f"- Profile: {headline.get('profile', 'n/a')}")
    lines.append(f"- Equity USD: {headline.get('equity_usd', 'n/a')}")
    lines.append(f"- Cash USD: {headline.get('cash_usd', 'n/a')}")
    lines.append(f"- Return pct: {headline.get('return_pct', 'n/a')}")
    lines.append(f"- Positions open: {headline.get('positions_open', 'n/a')}")
    lines.append(f"- Regime: {headline.get('regime', 'n/a')}")
    lines.append(f"- Allocator status: {headline.get('allocator_status', 'n/a')} ({headline.get('allocator_solver', 'n/a')})")
    lines.append("")
    lines.append("## Core Artifacts")
    for k, v in artifacts.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Runners")
    for k, v in runners.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Fast Restart Commands")
    for k, v in restart.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Moonshot Questions")
    for q in moonshot:
        lines.append(f"- {q}")
    lines.append("")
    lines.append("## Usage")
    lines.append("- Regenerate this file before opening a new chat.")
    lines.append("- Paste the resume prompt text file into the new chat first.")
    lines.append("")
    return "\n".join(lines)


def as_resume_prompt(snapshot: dict[str, Any]) -> str:
    payload = {
        "generated_utc": snapshot.get("generated_utc"),
        "objective": snapshot.get("objective"),
        "headline": snapshot.get("headline"),
        "artifact_paths": snapshot.get("artifact_paths"),
        "runner_paths": snapshot.get("runner_paths"),
        "opportunity_rollup": snapshot.get("opportunity_rollup"),
        "dashboard_health": snapshot.get("dashboard_health"),
        "restart_commands": snapshot.get("restart_commands"),
        "moonshot_questions_to_ask_next": snapshot.get("moonshot_questions_to_ask_next"),
        "instruction": "Continue from this exact state. Prioritize measured-vs-modeled audit-safe reporting, live dashboard reliability, and rolling sector opportunity gain improvements.",
    }
    return "<master-context>\n" + json.dumps(payload, indent=2) + "\n</master-context>\n"


def main() -> int:
    EXEC_OUT.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot()

    SNAPSHOT_JSON.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    SNAPSHOT_MD.write_text(as_markdown(snapshot), encoding="utf-8")
    RESUME_PROMPT_TXT.write_text(as_resume_prompt(snapshot), encoding="utf-8")

    print(f"Wrote {SNAPSHOT_JSON}")
    print(f"Wrote {SNAPSHOT_MD}")
    print(f"Wrote {RESUME_PROMPT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
