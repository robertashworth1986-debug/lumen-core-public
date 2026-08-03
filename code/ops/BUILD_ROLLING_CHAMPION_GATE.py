from __future__ import annotations

import json
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

TOP_REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
ENERGY_PRESSURE_JSON = OUT_OPS / "energy_price_pressure_forecast_latest.json"
LEDGER_JSONL = OUT_OPS / "rolling_champion_gate_ledger.jsonl"
OUT_JSON = OUT_OPS / "rolling_champion_gate_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "rolling_champion_gate.json"
OUT_MD = DOCS / "ROLLING_CHAMPION_GATE_2026-06-25.md"

EVIDENCE_BOUNDARY = (
    "A champion is not a one-off or context-derived win. This gate counts only v3 "
    "direct-measured, source-task-compatible replays that beat every registered "
    "source-specific baseline after global multiple-comparison correction. Historical "
    "live-context, source-conditioned synthetic, proxy, and fallback rows remain in the "
    "ledger but are excluded from promotion. This is not field validation, realized "
    "savings, live trading permission, or award certainty."
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


def sha256_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_ledger(path: Path = LEDGER_JSONL) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def append_ledger(entries: list[dict[str, Any]], path: Path = LEDGER_JSONL) -> None:
    if not entries:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_ledger(path)
    existing_keys = {(row.get("entity_id"), row.get("run_hash")) for row in existing}
    with path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            key = (entry.get("entity_id"), entry.get("run_hash"))
            if key in existing_keys:
                continue
            handle.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
            existing_keys.add(key)


def distinct_sources_from_card(card: dict[str, Any]) -> list[str]:
    sources = [
        str(source).strip().upper()
        for source in (
            card.get("direct_replay_source_names", [])
            + card.get("conditioned_stress_source_names", [])
        )
        if str(source).strip()
    ]
    return sorted(set(sources))


def entries_from_geometry_replay(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    run_base = payload.get("summary", {}).get("snapshot_chain_sha256") or payload.get("generated_utc") or sha256_payload(payload)
    for card in payload.get("replay_cards", []):
        if not isinstance(card, dict):
            continue
        family = str(
            card.get("evaluated_candidate_family_id")
            or card.get("candidate_family_id", "")
        ).strip()
        registered_family = str(card.get("candidate_family_id", "")).strip()
        lane = str(card.get("lane", "")).strip()
        if not family or not lane:
            continue
        candidate_beats = bool(card.get("candidate_beats_named_baseline"))
        evidence_mode = str(card.get("evidence_mode", "unclassified"))
        all_baselines_after_global_holm = bool(
            card.get("baseline_gauntlet", {}).get(
                "candidate_beats_all_registered_baselines_after_global_holm"
            )
        )
        qualified_repeat_win = bool(
            evidence_mode == "direct_measured_replay"
            and all_baselines_after_global_holm
        )
        sources = distinct_sources_from_card(card)
        run_hash = sha256_payload(
            {
                "run_base": run_base,
                "lane": lane,
                "family": family,
                "candidate_row": card.get("candidate_row", {}),
                "promotion_gate": card.get("promotion_gate", {}),
                "sources": sources,
            }
        )
        entries.append(
            {
                "schema": "rolling_champion_gate_entry.v2",
                "generated_utc": now_utc(),
                "domain": "geometry_compatibility_gated",
                "lane": lane,
                "entity_id": f"{lane}:{family}",
                "family_id": family,
                "registered_card_family_id": registered_family,
                "compatibility_contract_version": "geometry_live_wiring_matrix_v3",
                "evidence_mode": evidence_mode,
                "candidate_beats_named_baseline": candidate_beats,
                "candidate_beats_all_registered_baselines_after_global_holm": (
                    all_baselines_after_global_holm
                ),
                "qualified_repeat_win": qualified_repeat_win,
                "score_delta_vs_named_baseline": card.get("candidate_score_delta_vs_named_baseline"),
                "source_count": len(sources),
                "sources": sources,
                "run_hash": run_hash,
                "upstream_snapshot_chain_sha256": run_base,
                "field_validation": False,
                "ready_for_real_dollar_claim": False,
            }
        )
    return entries


def entries_from_energy_pressure(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not payload:
        return []
    summary = payload.get("summary", {})
    snapshots = payload.get("live_snapshot_profiles", {})
    sources = []
    if isinstance(snapshots, dict):
        for key, profile in snapshots.items():
            if isinstance(profile, dict) and int(profile.get("row_count", 0) or 0) > 0:
                sources.append(str(profile.get("source", key)).upper())
    sources.extend(["EIA_GRID_HOURLY_CSV", "EIA_NUCLEAR_OUTAGE_CSV", "FRED_MACRO_CSV"])
    sources = sorted(set(sources))
    entity = "energy_price_pressure:phase_locked_residual_corrector"
    evidence_hash = sha256_payload(
        {
            "entity": entity,
            "backtest": payload.get("backtest", {}),
            "forecast_rows": payload.get("forecast_rows", []),
            "live_snapshot_profiles": payload.get("live_snapshot_profiles", {}),
            "latest_grid_state": payload.get("latest_grid_state", {}),
            "sources": sources,
        }
    )
    run_hash = sha256_payload(
        {
            "entity": entity,
            "evidence_hash": evidence_hash,
            "summary": summary,
            "sources": sources,
        }
    )
    return [
        {
            "schema": "rolling_champion_gate_entry.v1",
            "generated_utc": now_utc(),
            "domain": "energy_price_pressure",
            "lane": "energy_price_pressure_proxy",
            "entity_id": entity,
            "family_id": "phase_locked_residual_corrector",
            "candidate_beats_named_baseline": bool(summary.get("phase_locked_beats_best_named_baseline")),
            "exploratory_mean_error_lower_than_named_baseline": bool(
                summary.get(
                    "exploratory_demand_proxy_mean_error_lower_than_best_named_baseline"
                )
            ),
            "compatibility_contract_version": "legacy_energy_proxy",
            "evidence_mode": "context_only_proxy",
            "candidate_beats_all_registered_baselines_after_global_holm": False,
            "qualified_repeat_win": False,
            "score_delta_vs_named_baseline": 0.0,
            "exploratory_improvement_vs_named_baseline_pct": summary.get(
                "exploratory_demand_proxy_improvement_pct"
            ),
            "source_count": len(sources),
            "sources": sources,
            "evidence_hash": evidence_hash,
            "run_hash": run_hash,
            "upstream_snapshot_chain_sha256": evidence_hash,
            "field_validation": False,
            "ready_for_real_dollar_claim": False,
        }
    ]


def normalized_evidence_hash(entry: dict[str, Any]) -> str:
    explicit = str(entry.get("evidence_hash", "")).strip()
    if explicit:
        return explicit
    domain = str(entry.get("domain", ""))
    base = {
        "domain": domain,
        "lane": entry.get("lane", ""),
        "entity_id": entry.get("entity_id", ""),
        "family_id": entry.get("family_id", ""),
        "candidate_beats_named_baseline": bool(entry.get("candidate_beats_named_baseline")),
        "qualified_repeat_win": bool(entry.get("qualified_repeat_win")),
        "compatibility_contract_version": entry.get(
            "compatibility_contract_version", "legacy_unclassified"
        ),
        "evidence_mode": entry.get("evidence_mode", "legacy_unclassified"),
        "score_delta_vs_named_baseline": entry.get("score_delta_vs_named_baseline"),
        "source_count": entry.get("source_count"),
        "sources": sorted(entry.get("sources", [])),
    }
    if domain != "energy_price_pressure":
        base["upstream_snapshot_chain_sha256"] = entry.get("upstream_snapshot_chain_sha256", "")
    return sha256_payload(base)
def status_for_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    qualified_entries = [
        entry
        for entry in entries
        if entry.get("compatibility_contract_version")
        == "geometry_live_wiring_matrix_v3"
        and entry.get("evidence_mode") == "direct_measured_replay"
    ]
    wins = [
        entry for entry in qualified_entries if bool(entry.get("qualified_repeat_win"))
    ]
    distinct_win_hashes = sorted({normalized_evidence_hash(entry) for entry in wins})
    all_sources = sorted(
        {
            source
            for entry in qualified_entries
            for source in entry.get("sources", [])
        }
    )
    latest = entries[-1] if entries else {}
    latest_qualified = qualified_entries[-1] if qualified_entries else {}
    repeat_live_wins = len(distinct_win_hashes)
    source_count = len(all_sources)
    if repeat_live_wins >= 2:
        status = "rolling_champion"
    elif wins:
        status = "single_run_candidate"
    else:
        status = "not_promoted"
    return {
        "entity_id": latest.get("entity_id", ""),
        "domain": latest.get("domain", ""),
        "lane": latest.get("lane", ""),
        "family_id": latest.get("family_id", ""),
        "status": status,
        "repeat_live_win_count": repeat_live_wins,
        "distinct_run_hash_count": len(
            {normalized_evidence_hash(entry) for entry in qualified_entries}
        ),
        "source_count": source_count,
        "sources": all_sources,
        "qualified_entry_count": len(qualified_entries),
        "historical_unqualified_entry_count": len(entries) - len(qualified_entries),
        "compatibility_contract_version": "geometry_live_wiring_matrix_v3",
        "latest_score_delta_vs_named_baseline": latest_qualified.get(
            "score_delta_vs_named_baseline"
        ),
        "ready_for_real_dollar_claim": False,
        "field_validation": False,
        "claim_language": (
            "Repeat v3 compatibility-gated direct measured champion evidence."
            if status == "rolling_champion"
            else (
                "One compatibility-gated direct measured win; repeat on a distinct frozen source window."
                if status == "single_run_candidate"
                else "Not promoted under the v3 direct-measured source-specific baseline contract."
            )
        ),
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Rolling Champion Gate",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Boundary",
        "",
        EVIDENCE_BOUNDARY,
        "",
        "## Summary",
        "",
        f"- Ledger entries: {payload['summary']['ledger_entry_count']}",
        f"- Rolling champions: {payload['summary']['rolling_champion_count']}",
        f"- Triple-source candidates: {payload['summary']['triple_source_candidate_count']}",
        f"- Single-run candidates: {payload['summary']['single_run_candidate_count']}",
        "",
        "## Promotion Board",
        "",
        "| Status | Entity | Repeat wins | Sources | Latest delta |",
        "|---|---|---:|---:|---:|",
    ]
    for row in payload.get("promotion_board", []):
        delta = row.get("latest_score_delta_vs_named_baseline")
        lines.append(
            f"| {row['status']} | {row['entity_id']} | {row['repeat_live_win_count']} | "
            f"{row['source_count']} | {delta if delta is not None else ''} |"
        )
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "- `rolling_champion`: at least two distinct live/frozen wins against a named baseline.",
            "- `single_run_candidate`: one v3-qualified direct measured win against every registered baseline after global correction.",
            "- `not_promoted`: no current v3-qualified direct measured win.",
            "- Historical context-only, proxy, synthetic-conditioning, and fallback entries remain auditable but do not count.",
        ]
    )
    return "\n".join(lines)


def build_payload() -> dict[str, Any]:
    geometry = read_json(TOP_REPLAY_JSON)
    energy = read_json(ENERGY_PRESSURE_JSON)
    new_entries = entries_from_geometry_replay(geometry) + entries_from_energy_pressure(energy)
    append_ledger(new_entries)
    ledger = read_ledger()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in ledger:
        entity = str(entry.get("entity_id", ""))
        if entity:
            grouped[entity].append(entry)
    board = [status_for_entries(entries) for _, entries in sorted(grouped.items())]
    status_order = {
        "rolling_champion": 0,
        "triple_source_candidate": 1,
        "single_run_candidate": 2,
        "not_promoted": 3,
    }
    board.sort(
        key=lambda row: (
            status_order.get(str(row.get("status")), 9),
            -int(row.get("repeat_live_win_count", 0) or 0),
            -int(row.get("source_count", 0) or 0),
            str(row.get("entity_id", "")),
        )
    )
    summary = {
        "new_entry_count": len(new_entries),
        "ledger_entry_count": len(ledger),
        "entity_count": len(board),
        "rolling_champion_count": sum(1 for row in board if row["status"] == "rolling_champion"),
        "triple_source_candidate_count": 0,
        "single_run_candidate_count": sum(1 for row in board if row["status"] == "single_run_candidate"),
        "not_promoted_count": sum(1 for row in board if row["status"] == "not_promoted"),
        "qualified_v3_entry_count": sum(
            int(row.get("qualified_entry_count", 0) or 0) for row in board
        ),
        "historical_unqualified_entry_count": sum(
            int(row.get("historical_unqualified_entry_count", 0) or 0)
            for row in board
        ),
        "ready_for_real_dollar_claim": False,
        "kraken_live_execution_allowed": False,
    }
    payload = {
        "schema": "rolling_champion_gate.v2",
        "generated_utc": now_utc(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "inputs": {
            "top_geometry_live_replay_results": str(TOP_REPLAY_JSON.relative_to(ROOT)),
            "energy_price_pressure_forecast": str(ENERGY_PRESSURE_JSON.relative_to(ROOT)),
            "ledger_jsonl": str(LEDGER_JSONL.relative_to(ROOT)),
        },
        "summary": summary,
        "promotion_board": board,
        "new_entries": new_entries,
    }
    payload["sha256"] = sha256_payload({key: value for key, value in payload.items() if key != "sha256"})
    return payload


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, build_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
