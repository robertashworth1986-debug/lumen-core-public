from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

ENV_FILES = [
    CONFIG / "luma_live_keys.env",
    ROOT / ".env.live",
    ROOT / ".env.sports",
]

OUT_JSON = OUT_OPS / "live_evidence_max_harvest_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "live_evidence_max_harvest.json"
OUT_MD = DOCS / f"LIVE_EVIDENCE_MAX_HARVEST_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"

SAFE_KEY_PING = ROOT / "code" / "ops" / "BUILD_SAFE_CREDENTIAL_PROVIDER_PING.py"
KEY_GATE = ROOT / "code" / "ops" / "BUILD_LIVE_BREADTH_KEY_GATE.py"
MAXIMIZER = ROOT / "code" / "ops" / "BUILD_LIVE_SOURCE_MEASUREMENT_MAXIMIZER.py"
WIRING = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_WIRING_MATRIX.py"
REPLAY = ROOT / "code" / "ops" / "BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py"
ENERGY_PRESSURE = ROOT / "code" / "ops" / "BUILD_ENERGY_PRICE_PRESSURE_FORECAST.py"
ROLLING_GATE = ROOT / "code" / "ops" / "BUILD_ROLLING_CHAMPION_GATE.py"

SOURCE_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
WIRING_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"
REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
ENERGY_PRESSURE_JSON = OUT_OPS / "energy_price_pressure_forecast_latest.json"
ROLLING_GATE_JSON = OUT_OPS / "rolling_champion_gate_latest.json"
EXTERNAL_INTAKE_JSON = OUT_OPS / "external_proof_drive_intake_latest.json"
PING_JSON = OUT_OPS / "safe_key_provider_ping_latest.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


def hydrate_env() -> dict[str, str]:
    loaded: dict[str, str] = {}
    for path in ENV_FILES:
        loaded.update(load_env_file(path))
    for key, value in loaded.items():
        if value and not os.environ.get(key):
            os.environ[key] = value
    return loaded


def tail(text: str, limit: int = 8000) -> str:
    return (text or "")[-limit:]


def run_step(label: str, script: Path, *, env: dict[str, str], timeout: int = 240, args: list[str] | None = None) -> dict[str, Any]:
    if not script.exists():
        return {
            "label": label,
            "script": str(script),
            "ok": False,
            "return_code": None,
            "started_utc": now_utc(),
            "ended_utc": now_utc(),
            "stdout_tail": "",
            "stderr_tail": "script not found",
        }
    started = now_utc()
    cmd = [sys.executable, str(script)] + list(args or [])
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "label": label,
            "script": str(script),
            "ok": proc.returncode == 0,
            "return_code": proc.returncode,
            "started_utc": started,
            "ended_utc": now_utc(),
            "stdout_tail": tail(proc.stdout),
            "stderr_tail": tail(proc.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "label": label,
            "script": str(script),
            "ok": False,
            "return_code": None,
            "started_utc": started,
            "ended_utc": now_utc(),
            "stdout_tail": tail(exc.stdout if isinstance(exc.stdout, str) else ""),
            "stderr_tail": f"timeout after {timeout}s",
        }
    except Exception as exc:
        return {
            "label": label,
            "script": str(script),
            "ok": False,
            "return_code": None,
            "started_utc": started,
            "ended_utc": now_utc(),
            "stdout_tail": "",
            "stderr_tail": f"{type(exc).__name__}: {exc}",
        }


def extract_summary() -> dict[str, Any]:
    source = read_json(SOURCE_JSON)
    wiring = read_json(WIRING_JSON)
    replay = read_json(REPLAY_JSON)
    energy_pressure = read_json(ENERGY_PRESSURE_JSON)
    rolling_gate = read_json(ROLLING_GATE_JSON)
    external_intake = read_json(EXTERNAL_INTAKE_JSON)
    ping = read_json(PING_JSON)

    source_summary = source.get("summary", {}) if isinstance(source, dict) else {}
    wiring_summary = wiring.get("summary", {}) if isinstance(wiring, dict) else {}
    replay_summary = replay.get("summary", {}) if isinstance(replay, dict) else {}
    energy_summary = energy_pressure.get("summary", {}) if isinstance(energy_pressure, dict) else {}
    rolling_summary = rolling_gate.get("summary", {}) if isinstance(rolling_gate, dict) else {}
    external_summary = external_intake.get("summary", {}) if isinstance(external_intake, dict) else {}
    ping_summary = ping.get("summary", {}) if isinstance(ping, dict) else {}

    return {
        "key_like_env_count": ping_summary.get("key_like_env_count"),
        "key_ready_provider_count": ping_summary.get("key_ready_provider_count"),
        "enabled_sources": source_summary.get("enabled_sources"),
        "measured_sources": source_summary.get("measured_sources"),
        "failed_or_thin_sources": source_summary.get("failed_or_thin_sources"),
        "total_measured_rows": source_summary.get("total_measured_rows"),
        "coverage_pct": source_summary.get("coverage_pct"),
        "estimated_annual_value_surface_usd": source_summary.get("estimated_annual_value_surface_usd"),
        "top_live_replay_source_map_count": wiring_summary.get("top_live_replay_source_map_count"),
        "top_live_replay_ready_count": wiring_summary.get("top_live_replay_ready_count"),
        "top_live_replay_measured_source_count": wiring_summary.get("top_live_replay_measured_source_count"),
        "adapter_replay_count": replay_summary.get("adapter_replay_count") or replay.get("adapter_replay_count"),
        "candidate_beats_named_baseline_count": replay_summary.get("candidate_beats_named_baseline_count") or replay.get("candidate_beats_named_baseline_count"),
        "paired_inference_card_count": replay_summary.get("paired_inference_card_count"),
        "holm_positive_card_count": replay_summary.get("holm_positive_card_count"),
        "registered_baseline_comparison_count": replay_summary.get("registered_baseline_comparison_count"),
        "registered_baseline_mean_win_count": replay_summary.get("registered_baseline_mean_win_count"),
        "registered_baseline_global_holm_positive_count": replay_summary.get("registered_baseline_global_holm_positive_count"),
        "cards_beating_all_registered_baselines_mean_count": replay_summary.get("cards_beating_all_registered_baselines_mean_count"),
        "cards_beating_all_registered_baselines_global_holm_count": replay_summary.get("cards_beating_all_registered_baselines_global_holm_count"),
        "time_series_measured_source_count": replay_summary.get("time_series_measured_source_count"),
        "time_series_measured_series_count": replay_summary.get("time_series_measured_series_count"),
        "total_live_context_rows_evaluated": replay_summary.get("total_live_context_rows_evaluated") or replay.get("total_live_context_rows_evaluated"),
        "unique_snapshot_sha256_count": replay_summary.get("unique_snapshot_sha256_count") or replay.get("unique_snapshot_sha256_count"),
        "snapshot_chain_sha256": replay_summary.get("snapshot_chain_sha256") or replay.get("snapshot_chain_sha256"),
        "energy_pressure_hourly_grid_rows": energy_summary.get("hourly_grid_rows"),
        "energy_pressure_forecast_rows": energy_summary.get("forecast_rows"),
        "energy_pressure_max_band": energy_summary.get("max_pressure_band"),
        "energy_pressure_phase_locked_improvement_pct": energy_summary.get("phase_locked_improvement_vs_best_named_baseline_pct"),
        "energy_pressure_ready_for_proxy_claim": bool(energy_summary.get("ready_for_price_pressure_claim")),
        "rolling_champion_count": rolling_summary.get("rolling_champion_count"),
        "triple_source_candidate_count": rolling_summary.get("triple_source_candidate_count"),
        "single_run_candidate_count": rolling_summary.get("single_run_candidate_count"),
        "external_drive_files_scanned": external_summary.get("files_seen"),
        "external_drive_candidate_count": external_summary.get("candidate_count"),
        "external_drive_live_frozen_triple_threat_candidate_count": external_summary.get("live_frozen_triple_threat_candidate_count"),
        "external_drive_research_candidate_count": external_summary.get("research_candidate_count"),
        "external_drive_content_hash_count": external_summary.get("content_hash_count"),
        "external_drive_delete_performed": bool(external_summary.get("delete_performed")),
        "ready_for_live_geometry_claim": bool(replay_summary.get("ready_for_live_geometry_claim") or replay.get("ready_for_live_geometry_claim")),
        "ready_for_real_dollar_claim": bool(
            replay_summary.get("ready_for_real_dollar_claim")
            or replay.get("ready_for_real_dollar_claim")
            or energy_summary.get("ready_for_real_dollar_claim")
            or rolling_summary.get("ready_for_real_dollar_claim")
        ),
        "kraken_live_execution_allowed": False,
    }


def next_actions(summary: dict[str, Any]) -> list[str]:
    actions = [
        "Add or rehydrate SAM_GOV_API_KEY so contract-bid discovery becomes measured instead of unconfigured.",
        "Fix the EPA_AQS email/key pair; the latest probe says the pair is invalid, not that the science lane is bad.",
        "Retry NASA and NREL from an unrestricted network session; the latest failures look like timeout/DNS, not rejected credentials.",
        "Retain the measured time-series loss against naive_last; redesign the candidate on a separate development set before another frozen evaluation.",
        "Keep appending distinct frozen live runs into the rolling champion ledger; do not promote a one-off win as a champion.",
        "Connect auditable ISO/RTO LMP or settlement price data to convert the energy pressure proxy into an actual price backtest.",
        "Convert the best live-context replay cards into a grant appendix with hashes, rows, baselines, and explicit claim boundaries.",
        "Review the external drive top candidates and promote only hash-backed live/frozen evidence into the proof rail; do not delete archive-review files automatically.",
    ]
    if summary.get("total_live_context_rows_evaluated", 0) and summary.get("candidate_beats_named_baseline_count", 0):
        actions.append("Keep the current claim language at live-context replay, not field validation, until a named external site or partner confirms outcomes.")
    actions.extend(
        [
            "Convert the measured economic surface into lane-specific investment signals by mapping measured rows to annualized value and replay-ready champion deltas.",
            "Execute the top live replay wiring cards against hashed measured snapshots so every geometry lane has a second validation path.",
            "Raise the sector breadth target: at least 10 live-measured sectors, with energy, rates, weather, market_data, and federal_opportunity all represented.",
            "Promote only hash-backed fresh measured snapshots into the proof rail; keep context-only or blocked sources as secondary support material.",
            "Use the external drive scan to add live/frozen triple-threat candidates only when they pass the same measured-source and hash-backed evidence gate.",
        ]
    )
    return actions


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Live Evidence Max Harvest",
        "",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Mode: `{payload['mode']}`",
        f"- Steps ok: `{payload['summary']['steps_ok']}/{payload['summary']['steps_count']}`",
        f"- Measured sources: `{summary.get('measured_sources')}` / enabled `{summary.get('enabled_sources')}`",
        f"- Total measured rows: `{summary.get('total_measured_rows')}`",
        f"- Live-context replay rows: `{summary.get('total_live_context_rows_evaluated')}`",
        f"- Candidate beats named baseline count: `{summary.get('candidate_beats_named_baseline_count')}`",
        f"- Cards with paired inference / positive after Holm: `{summary.get('paired_inference_card_count')}` / `{summary.get('holm_positive_card_count')}`",
        f"- Registered baseline comparisons / mean wins / global-Holm wins: `{summary.get('registered_baseline_comparison_count')}` / `{summary.get('registered_baseline_mean_win_count')}` / `{summary.get('registered_baseline_global_holm_positive_count')}`",
        f"- Cards beating all registered baselines by mean / global Holm: `{summary.get('cards_beating_all_registered_baselines_mean_count')}` / `{summary.get('cards_beating_all_registered_baselines_global_holm_count')}`",
        f"- Time-series measured sources/series: `{summary.get('time_series_measured_source_count')}` / `{summary.get('time_series_measured_series_count')}`",
        f"- Energy pressure rows/windows: `{summary.get('energy_pressure_hourly_grid_rows')}` / `{summary.get('energy_pressure_forecast_rows')}`",
        f"- Energy pressure max band: `{summary.get('energy_pressure_max_band')}`",
        f"- Energy pressure phase-locked improvement: `{summary.get('energy_pressure_phase_locked_improvement_pct')}`%",
        f"- Rolling champions / triple-source candidates: `{summary.get('rolling_champion_count')}` / `{summary.get('triple_source_candidate_count')}`",
        f"- External drive files/candidates/hash-backed top files: `{summary.get('external_drive_files_scanned')}` / `{summary.get('external_drive_candidate_count')}` / `{summary.get('external_drive_content_hash_count')}`",
        f"- External live-frozen triple-threat candidates: `{summary.get('external_drive_live_frozen_triple_threat_candidate_count')}`",
        f"- Snapshot chain SHA-256: `{summary.get('snapshot_chain_sha256')}`",
        f"- Ready for live geometry claim: `{str(summary.get('ready_for_live_geometry_claim')).lower()}`",
        f"- Ready for real dollar claim: `{str(summary.get('ready_for_real_dollar_claim')).lower()}`",
        f"- Kraken live execution allowed: `{str(summary.get('kraken_live_execution_allowed')).lower()}`",
        "",
        "## Step Results",
    ]
    for step in payload["steps"]:
        lines.append(f"- `{step['label']}`: ok `{str(step['ok']).lower()}`, return `{step['return_code']}`")
    lines.extend(["", "## Five Immediate Evidence Moves"])
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This harvest builds reproducible live-source, geometry-wiring, and live-context replay evidence. It does not authorize live trading, guarantee profit, prove field deployment, or certify any grant submission.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the safe live evidence harvest pipeline.")
    parser.add_argument("--skip-network", action="store_true", help="Skip the live-source maximizer network pull and reuse existing snapshots.")
    parser.add_argument("--extra-key-file", default="", help="Optional local key file to summarize without printing values.")
    parser.add_argument("--max-rows", type=int, default=250, help="Maximum rows requested from each provider.")
    parser.add_argument("--source-timeout", type=int, default=30, help="Per-provider network timeout in seconds.")
    args = parser.parse_args()

    hydrate_env()
    run_env = os.environ.copy()
    steps: list[dict[str, Any]] = []

    ping_args = ["--extra-key-file", args.extra_key_file] if args.extra_key_file else []
    steps.append(run_step("safe_key_provider_ping", SAFE_KEY_PING, env=run_env, timeout=120, args=ping_args))
    steps.append(run_step("live_breadth_key_gate", KEY_GATE, env=run_env, timeout=120))
    if args.skip_network:
        steps.append(
            {
                "label": "live_source_measurement_maximizer",
                "script": str(MAXIMIZER),
                "ok": True,
                "return_code": 0,
                "started_utc": now_utc(),
                "ended_utc": now_utc(),
                "stdout_tail": "skipped by --skip-network; using existing snapshots",
                "stderr_tail": "",
            }
        )
    else:
        maximizer_args = [
            "--max-rows",
            str(max(1, args.max_rows)),
            "--timeout",
            str(max(3, args.source_timeout)),
        ]
        steps.append(
            run_step(
                "live_source_measurement_maximizer",
                MAXIMIZER,
                env=run_env,
                timeout=max(300, len(maximizer_args) * max(3, args.source_timeout) * 10),
                args=maximizer_args,
            )
        )
    steps.append(run_step("geometry_live_wiring_matrix", WIRING, env=run_env, timeout=180))
    steps.append(run_step("top_geometry_live_replay_results", REPLAY, env=run_env, timeout=180))
    steps.append(run_step("energy_price_pressure_forecast", ENERGY_PRESSURE, env=run_env, timeout=180))
    steps.append(run_step("rolling_champion_gate", ROLLING_GATE, env=run_env, timeout=180))

    summary = extract_summary()
    summary["steps_count"] = len(steps)
    summary["steps_ok"] = len([step for step in steps if step.get("ok")])
    summary["mode"] = "reuse_existing_snapshots" if args.skip_network else "fresh_live_pull"
    summary["requested_max_rows_per_source"] = max(1, args.max_rows)
    summary["requested_source_timeout_seconds"] = max(3, args.source_timeout)

    payload = {
        "generated_utc": now_utc(),
        "schema": "live_evidence_max_harvest.v2",
        "mode": summary["mode"],
        "summary": summary,
        "steps": steps,
        "next_actions": next_actions(summary),
        "outputs": {
            "safe_key_provider_ping": str(PING_JSON),
            "live_source_measurement_maximizer": str(SOURCE_JSON),
            "geometry_live_wiring_matrix": str(WIRING_JSON),
            "top_geometry_live_replay_results": str(REPLAY_JSON),
            "energy_price_pressure_forecast": str(ENERGY_PRESSURE_JSON),
            "rolling_champion_gate": str(ROLLING_GATE_JSON),
            "dashboard_json": str(DASHBOARD_JSON),
            "markdown": str(OUT_MD),
        },
    }
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {DASHBOARD_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"steps_ok={summary['steps_ok']}/{summary['steps_count']}")
    return 0 if summary["steps_ok"] == summary["steps_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
