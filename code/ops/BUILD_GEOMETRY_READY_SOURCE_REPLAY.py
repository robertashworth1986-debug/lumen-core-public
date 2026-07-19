from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
MANIFEST_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_LIVE_SOURCE_MANIFEST.py"
TOP_REPLAY_SCRIPT = ROOT / "code" / "ops" / "BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py"

OUT_JSON = OUT_OPS / "geometry_ready_source_replay_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_ready_source_replay.json"
OUT_MD = DOCS / "GEOMETRY_READY_SOURCE_REPLAY_2026-06-26.md"

GEOMETRY_LANE_PRIORITY = (
    "optimal_curve_transport",
    "wave_resonance_timing",
    "thermal_ventilation",
    "branching_transport",
)

EVIDENCE_BOUNDARY = (
    "Geometry ready-source replay only. This reads local/uploaded measured files from the live source manifest, "
    "derives deterministic source profiles, and runs existing generated geometry benchmark adapters under equal "
    "candidate/baseline constraints. It is not field validation, not a clinical or addiction-treatment claim, "
    "not a trading signal, not realized savings, and not a fixed-dollar frozen-delta sales claim."
)

FORBIDDEN_CLAIM_TERMS = (
    "guaranteed award",
    "guaranteed profit",
    "live_order_placement",
    "heroin-like",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def file_sha256(path: Path, *, max_bytes: int | None = None) -> str:
    hasher = hashlib.sha256()
    remaining = max_bytes
    with path.open("rb") as handle:
        while True:
            if remaining is not None and remaining <= 0:
                break
            chunk_size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return hasher.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def ensure_manifest() -> dict[str, Any]:
    payload = read_json(MANIFEST_JSON)
    if payload.get("schema") == "geometry_live_source_manifest_v1":
        return payload
    module = load_module(MANIFEST_SCRIPT, "geometry_live_source_manifest_for_ready_replay")
    module.main()
    return read_json(MANIFEST_JSON)


def top_replay_module():
    return load_module(TOP_REPLAY_SCRIPT, "top_geometry_live_replay_for_ready_source")


def resolve_source_path(source_path: str) -> Path:
    path = Path(source_path)
    if path.is_absolute():
        return path
    return ROOT / source_path


def numeric_from_text(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    if any(ch.isalpha() for ch in text):
        return None
    if any(sep in text for sep in (":", "/")):
        return None
    if "-" in text and not text.lstrip().startswith("-"):
        return None
    cleaned = text.replace("$", "").replace("%", "").replace(",", "").strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    if not re.fullmatch(r"[-+]?\d+(\.\d+)?([eE][-+]?\d+)?", cleaned):
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def append_number(values: list[float], value: Any, sample_limit: int) -> None:
    if len(values) >= sample_limit:
        return
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        values.append(float(value))
        return
    if isinstance(value, str):
        number = numeric_from_text(value)
        if number is not None:
            values.append(number)


def collect_json_numbers(value: Any, values: list[float], sample_limit: int) -> None:
    if len(values) >= sample_limit:
        return
    if isinstance(value, dict):
        for item in value.values():
            collect_json_numbers(item, values, sample_limit)
            if len(values) >= sample_limit:
                return
    elif isinstance(value, list):
        for item in value:
            collect_json_numbers(item, values, sample_limit)
            if len(values) >= sample_limit:
                return
    else:
        append_number(values, value, sample_limit)


def read_numeric_samples(path: Path, sample_limit: int) -> list[float]:
    values: list[float] = []
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        try:
            with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
                reader = csv.reader(handle, delimiter=delimiter)
                for row in reader:
                    for cell in row:
                        append_number(values, cell, sample_limit)
                        if len(values) >= sample_limit:
                            return values
        except OSError:
            return values
        return values
    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            return values
        collect_json_numbers(payload, values, sample_limit)
        return values

    try:
        # Read only the bounded evidence window. Slicing read_text() after the
        # call still loads multi-gigabyte archives and text feeds in full.
        with path.open("rb") as handle:
            text = handle.read(2_000_000).decode("utf-8", errors="ignore")
    except OSError:
        return values
    for token in re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text):
        append_number(values, token, sample_limit)
        if len(values) >= sample_limit:
            break
    return values


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def source_profile(route: dict[str, Any], *, sample_limit: int) -> dict[str, Any]:
    source_path = str(route.get("source_path", ""))
    path = resolve_source_path(source_path)
    estimated_rows = int(route.get("estimated_rows") or 0)
    exists = path.exists()
    values = read_numeric_samples(path, sample_limit) if exists else []
    fallback_used = False
    if not values:
        fallback_used = True
        values = [float(max(estimated_rows, 1))]
    avg = mean(values)
    spread = pstdev(values) if len(values) > 1 else 0.0
    span = max(values) - min(values) if values else 0.0
    cv = spread / max(abs(avg), 1.0)
    diffs = [abs(b - a) for a, b in zip(values, values[1:])]
    shock = max(diffs) / max(abs(avg), 1.0) if diffs else 0.0
    trend = (values[-1] - values[0]) / max(abs(avg), 1.0) if len(values) > 1 else 0.0
    source_label = f"{route.get('system', 'source')}:{path.name}"
    seed_material = f"{source_path}|{estimated_rows}|{len(values)}"
    if exists:
        seed_material += "|" + file_sha256(path, max_bytes=2_000_000)
    seed = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:12], 16) % 900_000 + 10_000
    return {
        "source": source_label[:72],
        "source_path": source_path,
        "source_exists": exists,
        "estimated_rows": estimated_rows,
        "numeric_count": len(values) if not fallback_used else 0,
        "numeric_sample_limit": sample_limit,
        "fallback_used": fallback_used,
        "mean": round(avg, 6),
        "stddev": round(spread, 6),
        "span": round(span, 6),
        "coefficient_of_variation": round(cv, 6),
        "shock_index": round(shock, 6),
        "trend_index": round(trend, 6),
        "stress_index": round(clamp(0.45 * cv + 0.35 * shock + 0.20 * abs(trend), 0.0, 1.0), 6),
        "seed": seed,
        "source_sha256_prefix": file_sha256(path, max_bytes=2_000_000)[:16] if exists else "",
    }


def select_ready_routes(manifest: dict[str, Any], *, max_routes: int) -> list[dict[str, Any]]:
    rows = [
        row
        for row in manifest.get("manifest_rows", [])
        if isinstance(row, dict)
        and row.get("ready_for_benchmark")
        and row.get("lane") in GEOMETRY_LANE_PRIORITY
        and row.get("source_path")
    ]
    rows.sort(key=lambda item: (-int(item.get("estimated_rows") or 0), GEOMETRY_LANE_PRIORITY.index(item["lane"]), str(item.get("source_path", ""))))
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for lane in GEOMETRY_LANE_PRIORITY:
        for row in rows:
            key = (str(row.get("source_path")), str(row.get("lane")))
            if row.get("lane") == lane and key not in seen:
                selected.append(row)
                seen.add(key)
                break
    for row in rows:
        if len(selected) >= max_routes:
            break
        key = (str(row.get("source_path")), str(row.get("lane")))
        if key in seen:
            continue
        selected.append(row)
        seen.add(key)
    for idx, row in enumerate(selected, start=1):
        row["ready_source_replay_rank"] = idx
    return selected


def replay_route(route: dict[str, Any], replay: Any, *, sample_limit: int) -> dict[str, Any]:
    lane = str(route.get("lane", ""))
    candidate = str(route.get("candidate_family", ""))
    baseline = str(route.get("baseline_family", ""))
    profile = source_profile(route, sample_limit=sample_limit)
    adapter = replay.run_lane_adapter(lane, [profile])
    leaderboard = adapter.get("leaderboard", [])
    candidate_row = replay.find_leaderboard_row(leaderboard, candidate)
    baseline_row = replay.find_leaderboard_row(leaderboard, baseline)
    delta = None
    if candidate_row and baseline_row:
        delta = round(replay.score_value(candidate_row) - replay.score_value(baseline_row), 6)
    gate = adapter.get("promotion_gate", {}) if isinstance(adapter.get("promotion_gate"), dict) else {}
    result = {
        "rank": route.get("ready_source_replay_rank"),
        "lane": lane,
        "candidate_family": candidate,
        "baseline_family": baseline,
        "source_path": route.get("source_path", ""),
        "system": route.get("system", ""),
        "estimated_rows": int(route.get("estimated_rows") or 0),
        "profile": profile,
        "adapter_status": adapter.get("adapter_status", ""),
        "candidate_row": candidate_row,
        "baseline_row": baseline_row,
        "candidate_delta_vs_named_baseline": delta,
        "candidate_beats_named_baseline": bool(delta is not None and delta > 0),
        "best_geometry": gate.get("best_geometry", {}),
        "best_baseline": gate.get("best_baseline", {}),
        "promotion_gate": gate,
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
        },
        "evidence_boundary": "Source-conditioned generated benchmark replay; not a field or dollar claim.",
    }
    result["route_sha256"] = stable_sha256({k: v for k, v in result.items() if k != "route_sha256"})
    return result


def lane_scoreboard(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lanes: dict[str, dict[str, Any]] = {}
    for result in results:
        lane = result["lane"]
        item = lanes.setdefault(
            lane,
            {
                "lane": lane,
                "candidate_family": result["candidate_family"],
                "baseline_family": result["baseline_family"],
                "replay_count": 0,
                "candidate_win_count": 0,
                "estimated_rows": 0,
                "numeric_samples": 0,
                "mean_delta_vs_named_baseline": 0.0,
                "best_delta_vs_named_baseline": None,
            },
        )
        item["replay_count"] += 1
        item["estimated_rows"] += int(result.get("estimated_rows") or 0)
        item["numeric_samples"] += int(result.get("profile", {}).get("numeric_count") or 0)
        if result.get("candidate_beats_named_baseline"):
            item["candidate_win_count"] += 1
    for lane, item in lanes.items():
        deltas = [
            float(result["candidate_delta_vs_named_baseline"])
            for result in results
            if result["lane"] == lane and result.get("candidate_delta_vs_named_baseline") is not None
        ]
        item["mean_delta_vs_named_baseline"] = round(mean(deltas), 6) if deltas else None
        item["best_delta_vs_named_baseline"] = round(max(deltas), 6) if deltas else None
    out = list(lanes.values())
    out.sort(key=lambda item: (-int(item["candidate_win_count"]), -(item["best_delta_vs_named_baseline"] or -999), item["lane"]))
    return out


def next_ten_actions(results: list[dict[str, Any]], scoreboard: list[dict[str, Any]]) -> list[str]:
    strongest = max(
        (row for row in results if row.get("candidate_delta_vs_named_baseline") is not None),
        key=lambda row: float(row.get("candidate_delta_vs_named_baseline") or -999),
        default={},
    )
    strongest_lane = strongest.get("lane", "top ready lane")
    strongest_family = strongest.get("candidate_family", "top candidate")
    top_lane_names = ", ".join(row["lane"] for row in scoreboard[:3])
    return [
        f"Rerun `{strongest_family}` on `{strongest_lane}` with 20 deterministic holdout windows and freeze the split manifest.",
        "Run the same source-conditioned replay on the next 25 ready `wave_resonance_timing` sources to test whether Kuramoto survives broader live-context pressure.",
        "Run the next 25 ready `branching_transport` energy/grid/water/AIS routes and demote leaf-vein claims if the positive delta does not repeat.",
        "Run the next 10 `thermal_ventilation` EIA/cooling proxy files and keep thermal language as CFD/pilot-ready only.",
        "Build the missing adapter for `energy_price_pressure_proxy` so phase-locked residual correction can be compared to named forecasting baselines without trading language.",
        "Write a grant appendix table from only routes with positive replay deltas, source hashes, candidate/baseline names, and closed claim gates.",
        "Archive or re-map any high-row source that remains unclassified after the live source manifest so it does not inflate evidence counts.",
        f"Expose the lane scoreboard on the dashboard for `{top_lane_names}` with clear labels: generated replay, not field validation.",
        "Use the best positive route as the paid-pilot scoping example and ask the buyer to provide their incumbent baseline plus acceptance metric.",
        "Keep all public copy bounded: measured-source replay evidence, not realized savings, not grant certainty, not live trading, not medical treatment.",
    ]


def build_payload(*, max_routes: int = 10, sample_limit: int = 5_000) -> dict[str, Any]:
    manifest = ensure_manifest()
    selected = select_ready_routes(manifest, max_routes=max_routes)
    replay = top_replay_module()
    results = [replay_route(route, replay, sample_limit=sample_limit) for route in selected]
    scoreboard = lane_scoreboard(results)
    deltas = [float(row["candidate_delta_vs_named_baseline"]) for row in results if row.get("candidate_delta_vs_named_baseline") is not None]
    positive = [row for row in results if row.get("candidate_beats_named_baseline")]
    strongest = max(positive, key=lambda row: float(row.get("candidate_delta_vs_named_baseline") or -999), default={})
    summary = {
        "routes_replayed": len(results),
        "lanes_replayed": len({row["lane"] for row in results}),
        "source_files_replayed": len({row["source_path"] for row in results}),
        "estimated_rows_replayed": sum(int(row.get("estimated_rows") or 0) for row in results),
        "numeric_samples_read": sum(int(row.get("profile", {}).get("numeric_count") or 0) for row in results),
        "candidate_win_count": len(positive),
        "candidate_loss_or_tie_count": len(results) - len(positive),
        "mean_delta_vs_named_baseline": round(mean(deltas), 6) if deltas else None,
        "strongest_positive_delta": strongest.get("candidate_delta_vs_named_baseline"),
        "strongest_positive_family": strongest.get("candidate_family", ""),
        "strongest_positive_lane": strongest.get("lane", ""),
        "strongest_positive_source": strongest.get("source_path", ""),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "medical_or_addiction_treatment_claim_allowed": False,
    }
    payload = {
        "schema": "geometry_ready_source_replay_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "inputs": {
            "source_manifest": rel(MANIFEST_JSON),
            "top_replay_adapter": rel(TOP_REPLAY_SCRIPT),
        },
        "outputs": {"json": rel(OUT_JSON), "dashboard_json": rel(DASHBOARD_JSON), "markdown": rel(OUT_MD)},
        "summary": summary,
        "lane_scoreboard": scoreboard,
        "ready_source_replay_results": results,
        "next_ten_actions": next_ten_actions(results, scoreboard),
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "mass_email_allowed": False,
            "buyer_authorized_field_pilot_required": True,
        },
    }
    payload["summary"]["replay_chain_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "lane_scoreboard": payload["lane_scoreboard"],
            "ready_source_replay_results": [
                {
                    "lane": row["lane"],
                    "candidate_family": row["candidate_family"],
                    "baseline_family": row["baseline_family"],
                    "source_path": row["source_path"],
                    "delta": row["candidate_delta_vs_named_baseline"],
                    "route_sha256": row["route_sha256"],
                }
                for row in results
            ],
        }
    )
    serialized = json.dumps(payload, sort_keys=True, default=str).lower()
    for term in FORBIDDEN_CLAIM_TERMS:
        if term in serialized:
            raise ValueError(f"Forbidden claim term leaked into ready-source replay payload: {term}")
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Ready Source Replay",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Routes replayed: `{summary['routes_replayed']}`",
        f"- Lanes replayed: `{summary['lanes_replayed']}`",
        f"- Source files replayed: `{summary['source_files_replayed']}`",
        f"- Estimated rows replayed: `{summary['estimated_rows_replayed']}`",
        f"- Numeric samples read: `{summary['numeric_samples_read']}`",
        f"- Candidate wins vs named baselines: `{summary['candidate_win_count']}`",
        f"- Candidate loss/tie count: `{summary['candidate_loss_or_tie_count']}`",
        f"- Mean delta vs named baseline: `{summary['mean_delta_vs_named_baseline']}`",
        f"- Strongest positive family: `{summary['strongest_positive_family']}`",
        f"- Strongest positive lane: `{summary['strongest_positive_lane']}`",
        f"- Strongest positive delta: `{summary['strongest_positive_delta']}`",
        f"- Replay chain SHA-256: `{summary['replay_chain_sha256']}`",
        f"- Field validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        f"- Live trading/autonomous execution allowed: `{str(summary['live_trading_or_autonomous_execution_allowed']).lower()}`",
        "",
        "## Lane Scoreboard",
        "",
        "| Lane | Candidate | Baseline | Replays | Wins | Rows | Numeric Samples | Mean Delta | Best Delta |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["lane_scoreboard"]:
        lines.append(
            f"| `{row['lane']}` | `{row['candidate_family']}` | `{row['baseline_family']}` | "
            f"`{row['replay_count']}` | `{row['candidate_win_count']}` | `{row['estimated_rows']}` | "
            f"`{row['numeric_samples']}` | `{row['mean_delta_vs_named_baseline']}` | `{row['best_delta_vs_named_baseline']}` |"
        )

    lines.extend(["", "## Top Route Results", "", "| Rank | Lane | Candidate | Baseline | Delta | Source |", "| --- | --- | --- | --- | --- | --- |"])
    for row in payload["ready_source_replay_results"]:
        lines.append(
            f"| `{row['rank']}` | `{row['lane']}` | `{row['candidate_family']}` | `{row['baseline_family']}` | "
            f"`{row['candidate_delta_vs_named_baseline']}` | `{row['source_path']}` |"
        )

    lines.extend(["", "## Next 10 Actions", ""])
    for idx, action in enumerate(payload["next_ten_actions"], start=1):
        lines.append(f"{idx}. {action}")

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- This is source-conditioned replay evidence, not field validation.",
            "- Positive deltas are benchmark priorities until repeated on holdout windows and buyer/agency data.",
            "- No realized savings, fixed-dollar frozen-delta sales, medical, live-trading, or guaranteed award language is allowed.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
