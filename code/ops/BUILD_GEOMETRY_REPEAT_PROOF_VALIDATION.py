from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"
LIVE_MEASURED = ROOT / "data" / "live_measured"

TOP_REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
ASSET_MAP_JSON = OUT_OPS / "geometry_champion_asset_map_latest.json"
TOP_REPLAY_SCRIPT = ROOT / "code" / "ops" / "BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py"

OUT_JSON = OUT_OPS / "geometry_repeat_proof_validation_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_repeat_proof_validation.json"
OUT_MD = DOCS / "GEOMETRY_REPEAT_PROOF_VALIDATION_2026-06-25.md"

BOUNDARY = (
    "Repeat proof validation replays existing lane adapters against multiple distinct frozen live-source snapshots. "
    "It can strengthen candidate evidence, but it is not field validation, not realized savings, not a real-dollar "
    "claim, not award certainty, and not live trading permission."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
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


def load_top_replay_module():
    spec = importlib.util.spec_from_file_location("top_geometry_live_replay_results_repeat", TOP_REPLAY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def source_dir(source: str) -> str:
    return source.strip().lower()


def snapshot_index_for_source(source: str) -> dict[str, dict[str, Any]]:
    directory = LIVE_MEASURED / source_dir(source)
    if not directory.exists():
        return {}
    pattern = re.compile(r"_(\d{8}T\d{6}Z)\.json$", re.IGNORECASE)
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob(f"{source_dir(source)}_*.json")):
        match = pattern.search(path.name)
        if not match:
            continue
        payload = read_json(path)
        row_count = int(payload.get("row_count", 0) or 0)
        if row_count <= 0:
            continue
        digest = str(payload.get("sha256", ""))
        if not digest:
            continue
        timestamp = match.group(1)
        rows[timestamp] = {
            "source": str(payload.get("source", source)).upper(),
            "rows": row_count,
            "snapshot_json": str(path.relative_to(ROOT)).replace("\\", "/"),
            "snapshot_sha256": digest,
            "sector": payload.get("sector", ""),
            "generated_utc": payload.get("generated_utc", ""),
        }
    return rows


def common_windows(source_names: list[str]) -> tuple[dict[str, dict[str, dict[str, Any]]], list[str]]:
    indexes = {source: snapshot_index_for_source(source) for source in source_names}
    if not indexes or any(not value for value in indexes.values()):
        return indexes, []
    shared = sorted(set.intersection(*(set(value) for value in indexes.values())))
    return indexes, shared


def replay_window(
    top_module: Any,
    card: dict[str, Any],
    timestamp: str,
    source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    profiles = [top_module.snapshot_profile(row) for row in source_rows]
    adapter = top_module.run_lane_adapter(
        str(card.get("lane", "")), profiles, source_rows
    )
    leaderboard = adapter.get("leaderboard", [])
    candidate = str(card.get("candidate_family_id", ""))
    named_baseline = str(card.get("named_baseline", ""))
    candidate_row = top_module.find_leaderboard_row(leaderboard, candidate)
    baseline_row = top_module.find_leaderboard_row(leaderboard, named_baseline)
    delta = None
    if candidate_row and baseline_row:
        delta = round(top_module.score_value(candidate_row) - top_module.score_value(baseline_row), 6)
    source_hashes = sorted(row["snapshot_sha256"] for row in source_rows if row.get("snapshot_sha256"))
    result = {
        "timestamp": timestamp,
        "source_count": len(source_rows),
        "source_rows": source_rows,
        "source_chain_sha256": hashlib.sha256("\n".join(source_hashes).encode("utf-8")).hexdigest(),
        "adapter_status": adapter.get("adapter_status", ""),
        "candidate_family_id": candidate,
        "named_baseline": named_baseline,
        "candidate_score_delta_vs_named_baseline": delta,
        "candidate_beats_named_baseline": bool(delta is not None and delta > 0),
        "best_geometry_family_id": (adapter.get("promotion_gate", {}).get("best_geometry", {}) or {}).get(
            "family_id", ""
        ),
        "best_baseline_family_id": (adapter.get("promotion_gate", {}).get("best_baseline", {}) or {}).get(
            "family_id", ""
        ),
        "live_context_rows_evaluated": len(adapter.get("rows", [])),
        "leaderboard_head": [
            {
                "rank": row.get("rank"),
                "family_id": row.get("family_id", row.get("strategy", "")),
                "kind": row.get("kind", ""),
                "mean_score": row.get("mean_score", row.get("score")),
            }
            for row in leaderboard[:5]
        ],
    }
    result["window_result_sha256"] = stable_sha256(result)
    return result


def validate_card(top_module: Any, card: dict[str, Any]) -> dict[str, Any]:
    source_names = [
        str(profile.get("source", "")).upper()
        for profile in card.get("source_profiles", [])
        if isinstance(profile, dict) and profile.get("source")
    ]
    source_names = list(dict.fromkeys(source_names))
    indexes, timestamps = common_windows(source_names)
    window_results: list[dict[str, Any]] = []
    for timestamp in timestamps:
        source_rows = [indexes[source][timestamp] for source in source_names if timestamp in indexes[source]]
        if len(source_rows) != len(source_names):
            continue
        window_results.append(replay_window(top_module, card, timestamp, source_rows))

    win_results = [row for row in window_results if row["candidate_beats_named_baseline"]]
    distinct_win_hash_count = len({row["source_chain_sha256"] for row in win_results})
    distinct_window_hash_count = len({row["source_chain_sha256"] for row in window_results})
    min_source_count = min([row["source_count"] for row in window_results], default=0)
    candidate_best_count = sum(
        1 for row in window_results if row.get("best_geometry_family_id") == card.get("candidate_family_id")
    )
    repeat_gate_passed = (
        len(win_results) >= 2
        and distinct_win_hash_count >= 2
        and min_source_count >= 3
        and candidate_best_count >= 2
        and candidate_best_count >= 5
        and candidate_best_count * 2 >= len(window_results)
    )
    validation = {
        "family_id": card.get("candidate_family_id", ""),
        "lane": card.get("lane", ""),
        "named_baseline": card.get("named_baseline", ""),
        "source_names": source_names,
        "available_window_count": len(window_results),
        "min_source_count": min_source_count,
        "repeat_live_win_count": len(win_results),
        "distinct_window_hash_count": distinct_window_hash_count,
        "distinct_win_hash_count": distinct_win_hash_count,
        "candidate_best_geometry_count": candidate_best_count,
        "repeat_candidate_gate_passed": repeat_gate_passed,
        "evidence_stage": "repeat_live_candidate_not_field_validated"
        if repeat_gate_passed
        else "not_repeat_promoted",
        "window_results": window_results,
        "claim_gate": {
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "field_validation": False,
            "kraken_live_execution_allowed": False,
        },
        "claim_boundary": BOUNDARY,
    }
    validation["validation_sha256"] = stable_sha256(validation)
    return validation


def build_payload() -> dict[str, Any]:
    top_module = load_top_replay_module()
    top_replay = read_json(TOP_REPLAY_JSON)
    asset_map = read_json(ASSET_MAP_JSON)
    replay_cards = [
        card
        for card in top_replay.get("replay_cards", [])
        if isinstance(card, dict) and card.get("adapter_status") == "live_context_replay_ran"
    ]
    validations = [validate_card(top_module, card) for card in replay_cards]
    repeat_passed = [row for row in validations if row["repeat_candidate_gate_passed"]]
    gates = {
        "ready_for_live_geometry_claim": False,
        "ready_for_real_dollar_claim": False,
        "field_validation": False,
        "kraken_live_execution_allowed": False,
    }
    summary = {
        "validated_family_count": len(validations),
        "repeat_candidate_gate_passed_count": len(repeat_passed),
        "total_windows_replayed": sum(row["available_window_count"] for row in validations),
        "total_live_context_rows_evaluated": sum(
            window["live_context_rows_evaluated"]
            for row in validations
            for window in row["window_results"]
        ),
        "top_repeat_candidates": [
            {
                "family_id": row["family_id"],
                "lane": row["lane"],
                "repeat_live_win_count": row["repeat_live_win_count"],
                "distinct_win_hash_count": row["distinct_win_hash_count"],
                "min_source_count": row["min_source_count"],
            }
            for row in repeat_passed
        ],
        "validation_chain_sha256": stable_sha256(validations),
        **gates,
    }
    return {
        "schema": "geometry_repeat_proof_validation_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "top_geometry_live_replay_results": str(TOP_REPLAY_JSON.relative_to(ROOT)),
            "geometry_champion_asset_map": str(ASSET_MAP_JSON.relative_to(ROOT)),
            "top_replay_script": str(TOP_REPLAY_SCRIPT.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "asset_map_summary": asset_map.get("summary", {}),
        "summary": summary,
        "validations": validations,
        "claim_controls": {
            "allowed": [
                "repeat live-context candidate",
                "multiple frozen-source replay windows",
                "named-baseline repeat evidence",
                "grant or buyer pilot evidence annex",
            ],
            "blocked": [
                "field validation",
                "realized savings",
                "real-dollar claim",
                "award certainty",
                "live trading permission",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Repeat Proof Validation",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Validated families: `{summary['validated_family_count']}`",
        f"- Repeat candidate gates passed: `{summary['repeat_candidate_gate_passed_count']}`",
        f"- Total windows replayed: `{summary['total_windows_replayed']}`",
        f"- Live-context rows evaluated: `{summary['total_live_context_rows_evaluated']}`",
        f"- Ready for live geometry claim: `{str(summary['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Field validation: `{str(summary['field_validation']).lower()}`",
        f"- Validation chain SHA-256: `{summary['validation_chain_sha256']}`",
        "",
        "## Repeat Candidates",
        "",
    ]
    for candidate in summary["top_repeat_candidates"]:
        lines.append(
            f"- `{candidate['family_id']}` ({candidate['lane']}): "
            f"{candidate['repeat_live_win_count']} repeat wins, "
            f"{candidate['distinct_win_hash_count']} distinct winning source hashes, "
            f"minimum source count `{candidate['min_source_count']}`."
        )
    lines.extend(
        [
            "",
            "## Family Results",
            "",
            "| Family | Lane | Windows | Wins | Distinct Win Hashes | Min Sources | Gate |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["validations"]:
        lines.append(
            f"| `{row['family_id']}` | `{row['lane']}` | {row['available_window_count']} | "
            f"{row['repeat_live_win_count']} | {row['distinct_win_hash_count']} | "
            f"{row['min_source_count']} | `{str(row['repeat_candidate_gate_passed']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Controls",
            "",
            "- This strengthens repeat-live candidate evidence for rows that pass the gate.",
            "- It still does not prove field validation, realized savings, award certainty, live trading permission, or a real-dollar claim.",
            "- The next proof step is uncertainty/holdout reporting and buyer- or agency-authorized field data.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "validated_family_count": payload["summary"]["validated_family_count"],
                "repeat_candidate_gate_passed_count": payload["summary"]["repeat_candidate_gate_passed_count"],
                "total_windows_replayed": payload["summary"]["total_windows_replayed"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
