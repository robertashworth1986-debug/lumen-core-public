from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from dice_constraint_contract_benchmark import (  # noqa: E402
    AgentSpec,
    Condition,
    TaskSpec,
    TrialResult,
    run_protocol,
)


KRAKEN_HISTORY_DIR = ROOT / "data" / "kraken_hourly_history"
EIA_OUT_DIR = ROOT / "data" / "out"
OUT_ROOT = ROOT / "out" / "dice_live_breadth_replay"
OPS_OUT = ROOT / "out" / "ops"
GRANTS = ROOT / "grant_submissions"
DICE_DIR = GRANTS / "DICE_HR001126S0010"

OPS_JSON = OPS_OUT / "dice_live_breadth_replay_latest.json"
OPS_MD = DICE_DIR / "DICE_LIVE_BREADTH_REPLAY_2026-06-20.md"

EVIDENCE_BOUNDARY = (
    "Frozen live-pulled time-series replay adapter. Source rows are live-pulled "
    "or previously live-fetched operational/market signals, but task roles, "
    "risk tiers, and adversary knobs are deterministic derived labels for replay. "
    "Results do not establish DICE metric attainment, operational DoD performance, "
    "field validation, semantic correctness, or adversarial security."
)

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bUEI\s+[A-Z0-9]{8,16}\b", re.IGNORECASE),
    re.compile(r"\bCAGE/NCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
    re.compile(r"\bCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub(text: str) -> str:
    clean = text
    for pattern in SECRET_PATTERNS:
        clean = pattern.sub("[REDACTED]", clean)
    return clean


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def stable_seed(*parts: object) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big") % (2**31)


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_kraken_source(path: Path) -> dict[str, Any] | None:
    rows = read_csv_dicts(path)
    samples: list[dict[str, Any]] = []
    for row in rows:
        close = to_float(row.get("close"))
        if close <= 0:
            continue
        samples.append(
            {
                "time": row.get("time") or "",
                "value": close,
                "high": to_float(row.get("high"), close),
                "low": to_float(row.get("low"), close),
                "volume": to_float(row.get("volume")),
                "count": to_float(row.get("count")),
            }
        )
    if len(samples) < 24:
        return None
    source = path.stem.replace("ohlc_", "").replace("_", "/")
    return {
        "source_id": f"KRAKEN:{source}",
        "source_type": "market_execution",
        "path": path,
        "rows": samples,
        "sha256": sha256_file(path),
    }


def load_eia_source(path: Path) -> dict[str, Any] | None:
    rows = read_csv_dicts(path)
    samples: list[dict[str, Any]] = []
    for row in rows:
        value = to_float(row.get("value"))
        if value <= 0:
            continue
        samples.append(
            {
                "time": row.get("period") or row.get("time") or "",
                "value": value,
                "high": value,
                "low": value,
                "volume": value,
                "count": 1.0,
            }
        )
    if len(samples) < 24:
        return None
    respondent = rows[0].get("respondent") if rows else path.stem
    return {
        "source_id": f"EIA:{respondent or path.stem}",
        "source_type": "power_grid",
        "path": path,
        "rows": list(reversed(samples)),
        "sha256": sha256_file(path),
    }


def discover_sources(
    *,
    max_kraken: int = 4,
    max_eia: int = 2,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    kraken_files = sorted(KRAKEN_HISTORY_DIR.glob("ohlc_*_USD.csv"))
    scored_kraken: list[tuple[float, dict[str, Any]]] = []
    for path in kraken_files:
        source = load_kraken_source(path)
        if not source:
            continue
        rows = source["rows"]
        activity = sum(float(row.get("count") or 0.0) for row in rows)
        scored_kraken.append((activity, source))
    for _, source in sorted(scored_kraken, key=lambda item: item[0], reverse=True)[:max_kraken]:
        sources.append(source)

    eia_files = sorted(EIA_OUT_DIR.glob("live_eia_*.csv"))
    for path in eia_files[:max_eia]:
        source = load_eia_source(path)
        if source:
            sources.append(source)
    return sources


def returns_for(rows: list[dict[str, Any]]) -> list[float]:
    values = [float(row["value"]) for row in rows if float(row.get("value") or 0.0) > 0.0]
    out: list[float] = []
    for previous, current in zip(values, values[1:]):
        if previous > 0:
            out.append((current - previous) / previous)
    return out


def window_stats(rows: list[dict[str, Any]]) -> dict[str, float]:
    returns = returns_for(rows)
    abs_returns = [abs(value) for value in returns]
    counts = [float(row.get("count") or 0.0) for row in rows]
    values = [float(row.get("value") or 0.0) for row in rows]
    ranges = [
        abs(float(row.get("high") or value) - float(row.get("low") or value)) / max(value, 1e-9)
        for row, value in zip(rows, values)
    ]
    mean_return = mean(returns) if returns else 0.0
    variance = mean([(value - mean_return) ** 2 for value in returns]) if returns else 0.0
    zero_activity = mean([1.0 if count <= 0 else 0.0 for count in counts]) if counts else 0.0
    spike_threshold = max(0.0025, percentile(abs_returns, 0.80))
    spike_fraction = (
        mean([1.0 if value >= spike_threshold else 0.0 for value in abs_returns])
        if abs_returns
        else 0.0
    )
    return {
        "mean_return": mean_return,
        "volatility": math.sqrt(variance),
        "zero_activity_fraction": zero_activity,
        "spike_fraction": spike_fraction,
        "range_mean": mean(ranges) if ranges else 0.0,
        "rows": float(len(rows)),
    }


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def condition_from_window(source_id: str, index: int, stats: dict[str, float]) -> Condition:
    volatility = stats["volatility"]
    zero_activity = stats["zero_activity_fraction"]
    spike_fraction = stats["spike_fraction"]
    failed = clamp(0.03 + zero_activity * 0.16 + volatility * 1.5, 0.03, 0.18)
    compromised = clamp(0.02 + spike_fraction * 0.13 + volatility * 0.9, 0.02, 0.20)
    collusive = clamp(0.15 + spike_fraction * 0.75, 0.15, 0.90)
    monitor_noise = clamp(0.03 + zero_activity * 0.35 + volatility * 2.8, 0.03, 0.24)
    stale = clamp(0.02 + zero_activity * 0.30 + spike_fraction * 0.05, 0.02, 0.16)
    safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", source_id).strip("_")
    return Condition(
        name=f"live_{safe_name}_w{index:02d}",
        failed_fraction=failed,
        compromised_fraction=compromised,
        collusive_fraction=collusive,
        monitor_noise=monitor_noise,
        stale_evidence_fraction=stale,
    )


def population_from_condition(seed: int, agents: int, roles: int, condition: Condition) -> list[AgentSpec]:
    ordering = sorted(range(agents), key=lambda agent_id: stable_seed(seed, "state", agent_id))
    failed_count = round(agents * condition.failed_fraction)
    compromised_count = round(agents * condition.compromised_fraction)
    failed = set(ordering[:failed_count])
    compromised = set(ordering[failed_count : failed_count + compromised_count])
    population: list[AgentSpec] = []
    for agent_id in range(agents):
        attack_roll = stable_seed(seed, "attack", agent_id) / float(2**31)
        if agent_id not in compromised:
            attack_mode = "honest"
        elif attack_roll < condition.collusive_fraction:
            attack_mode = "consistent_collusion"
        elif attack_roll < condition.collusive_fraction + 0.55 * (1.0 - condition.collusive_fraction):
            attack_mode = "malformed_contract"
        else:
            attack_mode = "stale_lineage"
        population.append(
            AgentSpec(
                agent_id=agent_id,
                role=agent_id % roles,
                skill=0.58 + 0.38 * (stable_seed(seed, "skill", agent_id) / float(2**31)),
                coherence_horizon=4 + stable_seed(seed, "horizon", agent_id) % 13,
                strategy=agent_id % 8,
                failed=agent_id in failed,
                compromised=agent_id in compromised,
                attack_mode=attack_mode,
            )
        )
    return population


def tasks_from_window(
    rows: list[dict[str, Any]],
    *,
    seed: int,
    roles: int,
    task_multiplier: int,
) -> list[TaskSpec]:
    returns = [0.0] + returns_for(rows)
    abs_returns = [abs(value) for value in returns]
    high_bar = max(0.0025, percentile(abs_returns, 0.75))
    tasks: list[TaskSpec] = []
    task_id = 0
    for index, row in enumerate(rows):
        shock = abs_returns[index] if index < len(abs_returns) else 0.0
        count = float(row.get("count") or 0.0)
        range_pct = abs(float(row.get("high") or row["value"]) - float(row.get("low") or row["value"])) / max(float(row["value"]), 1e-9)
        risk_tier = 3 if shock >= high_bar or range_pct >= high_bar else 2 if count <= 1 else 1
        horizon = 3 + min(12, int(round((shock + range_pct) / max(high_bar, 1e-9) * 4.0)))
        role_base = stable_seed(seed, "role", index) % roles
        for repeat in range(task_multiplier):
            tasks.append(
                TaskSpec(
                    task_id=task_id,
                    role=(role_base + repeat) % roles,
                    required_horizon=horizon,
                    evidence_epoch=index,
                    risk_tier=risk_tier,
                )
            )
            task_id += 1
    return tasks


def make_windows(
    rows: list[dict[str, Any]],
    *,
    window_size: int,
    scenarios_per_source: int,
) -> list[list[dict[str, Any]]]:
    if len(rows) < window_size:
        return []
    if scenarios_per_source <= 1:
        return [rows[-window_size:]]
    max_start = len(rows) - window_size
    starts = sorted({round(max_start * idx / max(1, scenarios_per_source - 1)) for idx in range(scenarios_per_source)})
    return [rows[start : start + window_size] for start in starts if len(rows[start : start + window_size]) == window_size]


def paired_summaries(rows: list[TrialResult]) -> dict[str, Any]:
    by_seed: dict[int, dict[str, TrialResult]] = {}
    for row in rows:
        by_seed.setdefault(row.seed, {})[row.architecture] = row
    pairs = [pair for pair in by_seed.values() if {"peer_reputation", "constraint_contract"} <= set(pair)]

    def delta(metric: str, higher_is_better: bool) -> dict[str, Any]:
        values = [getattr(pair["constraint_contract"], metric) - getattr(pair["peer_reputation"], metric) for pair in pairs]
        if not values:
            return {"mean_delta": 0.0, "favorable_scenario_fraction": 0.0, "scenario_count": 0}
        favorable = [value > 0 if higher_is_better else value < 0 for value in values]
        return {
            "mean_delta": mean(values),
            "min_delta": min(values),
            "max_delta": max(values),
            "favorable_scenario_fraction": mean(float(value) for value in favorable),
            "scenario_count": len(values),
        }

    return {
        "safe_completion_rate": delta("safe_completion_rate", True),
        "constraint_violation_rate": delta("constraint_violation_rate", False),
        "messages_per_safe_completion": delta("messages_per_safe_completion", False),
        "false_rejection_rate": delta("false_rejection_rate", False),
    }


def aggregate_by_architecture(rows: list[TrialResult]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    metrics = [
        "safe_completion_rate",
        "raw_completion_rate",
        "constraint_violation_rate",
        "compromised_assignment_rate",
        "messages_per_safe_completion",
        "false_rejection_rate",
        "strategy_entropy",
        "unavailable_task_rate",
    ]
    for architecture in ("peer_reputation", "constraint_contract"):
        subset = [row for row in rows if row.architecture == architecture]
        output[architecture] = {
            metric: mean(float(getattr(row, metric)) for row in subset) if subset else 0.0
            for metric in metrics
        }
    return output


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def render_scorecard(summary: dict[str, Any]) -> str:
    paired = summary["paired_metrics"]
    lines = [
        "# DICE Live Breadth Replay",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Evidence Boundary",
        "",
        f"- Evidence mode: {summary.get('evidence_mode', '')}",
        f"- Primary evidence source: {summary.get('primary_evidence_source', '')}",
        f"- Synthetic role: {summary.get('synthetic_role', '')}",
        "",
        summary["evidence_boundary"],
        "",
        "## Replay Scope",
        "",
        f"- Source count: {summary['source_manifest']['source_count']}",
        f"- Scenario windows: {summary['configuration']['scenario_count']}",
        f"- Agents per scenario: {summary['configuration']['agents']}",
        f"- Roles: {summary['configuration']['roles']}",
        f"- Task multiplier per live row: {summary['configuration']['task_multiplier']}",
        "",
        "## Paired Replay Metrics",
        "",
        "| Metric | Mean delta | Favorable fraction | Scenario count |",
        "|---|---:|---:|---:|",
        f"| Safe completion | {paired['safe_completion_rate']['mean_delta']:+.4f} | {paired['safe_completion_rate']['favorable_scenario_fraction']:.3f} | {paired['safe_completion_rate']['scenario_count']} |",
        f"| Constraint violation | {paired['constraint_violation_rate']['mean_delta']:+.4f} | {paired['constraint_violation_rate']['favorable_scenario_fraction']:.3f} | {paired['constraint_violation_rate']['scenario_count']} |",
        f"| Messages per safe completion | {paired['messages_per_safe_completion']['mean_delta']:+.4f} | {paired['messages_per_safe_completion']['favorable_scenario_fraction']:.3f} | {paired['messages_per_safe_completion']['scenario_count']} |",
        f"| False rejection | {paired['false_rejection_rate']['mean_delta']:+.4f} | {paired['false_rejection_rate']['favorable_scenario_fraction']:.3f} | {paired['false_rejection_rate']['scenario_count']} |",
        "",
        "## Source Windows",
        "",
        "| Source | Type | Windows | Rows | SHA-256 prefix |",
        "|---|---|---:|---:|---|",
    ]
    for source in summary["source_manifest"]["sources"]:
        lines.append(
            f"| {source['source_id']} | {source['source_type']} | "
            f"{source['window_count']} | {source['row_count']} | {source['sha256'][:12]} |"
        )
    lines.extend(
        [
            "",
            "## Claim Gate",
            "",
            "- ready_for_portal_upload: false",
            "- ready_for_submit: false",
            "- live_replay_proves_dice_metric_attainment: false",
            "- live_replay_proves_operational_performance: false",
            "- live_replay_proves_trading_profit: false",
            "- synthetic_primary_evidence: false",
            "",
        ]
    )
    return scrub("\n".join(lines))


def manifest_for(paths: list[Path], generated_utc: str) -> dict[str, Any]:
    return {
        "schema": "dice_live_breadth_replay_manifest_v1",
        "generated_utc": generated_utc,
        "files": {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in paths
        },
    }


def build_replay(
    *,
    out_dir: Path,
    max_kraken: int = 4,
    max_eia: int = 2,
    window_size: int = 48,
    scenarios_per_source: int = 3,
    agents: int = 180,
    roles: int = 8,
    task_multiplier: int = 3,
    margin: int = 0,
) -> dict[str, Any]:
    sources = discover_sources(max_kraken=max_kraken, max_eia=max_eia)
    if not sources:
        raise RuntimeError("No eligible live breadth source files found for replay")
    out_dir.mkdir(parents=True, exist_ok=False)

    trial_rows: list[TrialResult] = []
    scenario_rows: list[dict[str, Any]] = []
    source_manifest_rows: list[dict[str, Any]] = []
    for source_index, source in enumerate(sources):
        windows = make_windows(
            source["rows"],
            window_size=window_size,
            scenarios_per_source=scenarios_per_source,
        )
        source_manifest_rows.append(
            {
                "source_id": source["source_id"],
                "source_type": source["source_type"],
                "path": rel(Path(source["path"])),
                "sha256": source["sha256"],
                "row_count": len(source["rows"]),
                "window_count": len(windows),
            }
        )
        for window_index, window in enumerate(windows):
            seed = stable_seed(source["source_id"], source["sha256"], window_index)
            stats = window_stats(window)
            condition = condition_from_window(source["source_id"], window_index, stats)
            population = population_from_condition(seed, agents, roles, condition)
            tasks = tasks_from_window(
                window,
                seed=seed,
                roles=roles,
                task_multiplier=task_multiplier,
            )
            scenario_rows.append(
                {
                    "scenario_id": condition.name,
                    "source_id": source["source_id"],
                    "source_type": source["source_type"],
                    "seed": seed,
                    "window_index": window_index,
                    "window_rows": len(window),
                    "tasks": len(tasks),
                    "failed_fraction": condition.failed_fraction,
                    "compromised_fraction": condition.compromised_fraction,
                    "collusive_fraction": condition.collusive_fraction,
                    "monitor_noise": condition.monitor_noise,
                    "stale_evidence_fraction": condition.stale_evidence_fraction,
                    **stats,
                }
            )
            for architecture in ("peer_reputation", "constraint_contract"):
                trial_rows.append(
                    run_protocol(
                        seed=seed,
                        population=population,
                        tasks=tasks,
                        condition=condition,
                        architecture=architecture,
                        margin=margin,
                    )
                )

    generated_utc = now_utc()
    source_manifest = {
        "schema": "dice_live_breadth_source_manifest_v1",
        "generated_utc": generated_utc,
        "source_count": len(source_manifest_rows),
        "sources": source_manifest_rows,
    }
    summary = {
        "schema": "dice_live_breadth_replay_v1",
        "generated_utc": generated_utc,
        "evidence_mode": "primary_live_pulled_source_rows_with_deterministic_replay_labels",
        "primary_evidence_source": "frozen_live_pulled_rows",
        "synthetic_role": "secondary_control_labels_ablation_and_failure_injection_only",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "configuration": {
            "max_kraken": max_kraken,
            "max_eia": max_eia,
            "window_size": window_size,
            "scenarios_per_source": scenarios_per_source,
            "scenario_count": len(scenario_rows),
            "agents": agents,
            "roles": roles,
            "task_multiplier": task_multiplier,
            "margin": margin,
        },
        "source_manifest": source_manifest,
        "aggregate": aggregate_by_architecture(trial_rows),
        "paired_metrics": paired_summaries(trial_rows),
        "limitations": [
            "Live rows are converted into deterministic replay labels; source data do not carry native DICE task labels.",
            "No language-model inference, tool-use memory, or TA3 adaptor is evaluated.",
            "No field or partner validation is implied.",
            "Trading/market data are used only as stress and timing signals for replay, not as grant-merit or profit proof.",
        ],
        "claim_gate": {
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
            "live_replay_proves_dice_metric_attainment": False,
            "live_replay_proves_operational_performance": False,
            "live_replay_proves_trading_profit": False,
            "synthetic_primary_evidence": False,
        },
    }

    source_manifest_path = out_dir / "source_manifest.json"
    scenarios_path = out_dir / "scenarios.csv"
    trials_path = out_dir / "trials.csv"
    summary_path = out_dir / "summary.json"
    scorecard_path = out_dir / "SCORECARD.md"

    write_json(source_manifest_path, source_manifest)
    write_csv(
        scenarios_path,
        scenario_rows,
        [
            "scenario_id",
            "source_id",
            "source_type",
            "seed",
            "window_index",
            "window_rows",
            "tasks",
            "failed_fraction",
            "compromised_fraction",
            "collusive_fraction",
            "monitor_noise",
            "stale_evidence_fraction",
            "mean_return",
            "volatility",
            "zero_activity_fraction",
            "spike_fraction",
            "range_mean",
            "rows",
        ],
    )
    write_csv(trials_path, [asdict(row) for row in trial_rows], list(asdict(trial_rows[0])))
    write_json(summary_path, summary)
    scorecard_path.write_text(render_scorecard(summary), encoding="utf-8")
    manifest_path = out_dir / "manifest.sha256.json"
    write_json(
        manifest_path,
        manifest_for(
            [source_manifest_path, scenarios_path, trials_path, summary_path, scorecard_path],
            generated_utc,
        ),
    )
    return summary


def write_latest_outputs(summary: dict[str, Any]) -> None:
    OPS_OUT.mkdir(parents=True, exist_ok=True)
    DICE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OPS_JSON, summary)
    OPS_MD.write_text(render_scorecard(summary), encoding="utf-8")


def main() -> int:
    tag = now_tag()
    out_dir = OUT_ROOT / tag
    summary = build_replay(out_dir=out_dir)
    write_latest_outputs(summary)
    print(
        json.dumps(
            {
                "schema": summary["schema"],
                "scenario_count": summary["configuration"]["scenario_count"],
                "source_count": summary["source_manifest"]["source_count"],
                "safe_completion_delta": summary["paired_metrics"]["safe_completion_rate"]["mean_delta"],
                "out_dir": rel(out_dir),
                "latest_json": rel(OPS_JSON),
                "latest_md": rel(OPS_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
