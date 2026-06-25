from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

QUEUE_JSON = OUT_OPS / "geometry_live_breadth_proof_queue_latest.json"
REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
CHAMPIONS_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
ROLLING_JSON = OUT_OPS / "rolling_champion_gate_latest.json"

OUT_JSON = OUT_OPS / "geometry_proof_card_pack_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_proof_card_pack.json"
OUT_MD = DOCS / "GEOMETRY_PROOF_CARD_PACK_2026-06-25.md"

BOUNDARY = (
    "Proof cards package ranked evidence for review. They do not establish field validation, realized savings, "
    "trading profit, award certainty, or a real-dollar claim."
)

BLOCKED_LANGUAGE = [
    "guaranteed winner",
    "field validated",
    "realized savings",
    "customer ROI proven",
    "government savings proven",
    "trading profit proven",
    "grant award guaranteed",
]


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item.get(key, "")): item for item in items if isinstance(item, dict) and item.get(key)}


def replay_sources(card: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for source in card.get("source_profiles", []):
        if not isinstance(source, dict):
            continue
        rows.append(
            {
                "source": source.get("source", ""),
                "rows": int(source.get("row_count", 0) or 0),
                "snapshot_json": source.get("snapshot_json", ""),
                "snapshot_sha256": source.get("snapshot_sha256", ""),
                "stress_index": source.get("stress_index", 0.0),
                "shock_index": source.get("shock_index", 0.0),
                "trend_index": source.get("trend_index", 0.0),
            }
        )
    return rows


def leaderboard_head(card: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in card.get("leaderboard", [])[:5]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "rank": item.get("rank"),
                "family_id": item.get("family_id", item.get("strategy", "")),
                "kind": item.get("kind", ""),
                "mean_score": item.get("mean_score", item.get("score")),
            }
        )
    return rows


def readiness_tier(family: dict[str, Any], replay: dict[str, Any], rolling: dict[str, Any]) -> str:
    rolling_status = str(family.get("rolling_gate_status") or rolling.get("status") or "not_in_rolling_gate")
    if rolling_status == "rolling_champion":
        return "repeat_rolling_champion_still_needs_field_validation"
    if rolling_status == "triple_source_candidate" and not replay:
        return "triple_source_candidate_needs_registry_or_replay_adapter"
    if rolling_status == "triple_source_candidate" and replay.get("candidate_beats_named_baseline"):
        return "triple_source_candidate_ready_for_repeat_replay"
    if rolling_status == "single_run_candidate":
        return "single_run_candidate_needs_more_sources_or_repeat"
    if family.get("is_proof_value_champion"):
        return "proof_value_priority_needs_live_win"
    if replay and replay.get("candidate_beats_named_baseline") is False:
        return "replay_candidate_did_not_beat_named_baseline"
    if replay and replay.get("adapter_status") != "live_context_replay_ran":
        return "source_context_only_needs_lane_adapter"
    return "ranked_for_future_validation"


def allowed_language(tier: str, family: dict[str, Any]) -> str:
    if tier == "triple_source_candidate_ready_for_repeat_replay":
        return (
            f"Allowed: {family.get('label') or family.get('family_id')} is a promising triple-source live-context "
            "candidate that needs repeat frozen runs before stronger claims."
        )
    if tier == "single_run_candidate_needs_more_sources_or_repeat":
        return "Allowed: single-run candidate evidence; use only to justify the next repeat/source-expansion experiment."
    if tier == "proof_value_priority_needs_live_win":
        return "Allowed: high proof-value target; do not call it a performance winner until it wins live replay gates."
    if tier == "replay_candidate_did_not_beat_named_baseline":
        return "Allowed: negative/failed replay evidence; use it to redirect validation toward the actual best geometry."
    if tier == "source_context_only_needs_lane_adapter":
        return "Allowed: source context exists, but no lane adapter result yet."
    return "Allowed: ranked research candidate only."


def next_steps(tier: str, family: dict[str, Any]) -> list[str]:
    base = [
        "Freeze the next live/public source window and record SHA-256 hashes before replay.",
        "Run the exact named baselines on the same frozen window.",
        "Report uncertainty, holdout or walk-forward split, and multiple-comparison boundary.",
        "Do not promote to dollar or field-validation language without an authorized operational source.",
    ]
    if tier == "triple_source_candidate_ready_for_repeat_replay":
        return [
            "Repeat this candidate on a second distinct frozen run hash.",
            "Add at least one independent source window not used in the first replay.",
            *base,
        ]
    if tier == "single_run_candidate_needs_more_sources_or_repeat":
        return [
            "Increase source count to at least three measured sources or repeat on a second frozen run.",
            *base,
        ]
    if tier == "proof_value_priority_needs_live_win":
        return [
            "Build the first replay adapter or reroute to the current best live replay geometry.",
            *base,
        ]
    return base


def card_from_family(
    family_id: str,
    family: dict[str, Any],
    replay: dict[str, Any],
    rolling: dict[str, Any],
    replay_summary: dict[str, Any],
) -> dict[str, Any]:
    tier = readiness_tier(family, replay, rolling)
    result = {
        "adapter_status": replay.get("adapter_status", "not_replayed"),
        "candidate_beats_named_baseline": replay.get("candidate_beats_named_baseline"),
        "candidate_score_delta_vs_named_baseline": replay.get("candidate_score_delta_vs_named_baseline"),
        "best_geometry_family_id": replay.get("best_geometry_family_id", ""),
        "best_baseline_family_id": replay.get("best_baseline_family_id", ""),
        "live_context_rows_evaluated": int(replay.get("live_context_rows_evaluated", 0) or 0),
        "leaderboard_head": leaderboard_head(replay),
    }
    if not replay and rolling:
        delta = rolling.get("latest_score_delta_vs_named_baseline")
        result.update(
            {
                "adapter_status": "external_rolling_gate_annex_no_geometry_adapter",
                "candidate_beats_named_baseline": bool(delta is not None and float(delta or 0) > 0),
                "candidate_score_delta_vs_named_baseline": delta,
                "live_context_rows_evaluated": 0,
            }
        )
    sources = replay_sources(replay)
    if not sources and rolling.get("sources"):
        sources = [{"source": source, "rows": 0, "snapshot_json": "", "snapshot_sha256": "", "stress_index": 0.0} for source in rolling.get("sources", [])]
    card = {
        "family_id": family_id,
        "label": family.get("label", family_id),
        "lane": family.get("lane", rolling.get("lane", "")),
        "registry_family": bool(family),
        "proof_asset": family.get("proof_asset", "External rolling-gate annex card"),
        "readiness_tier": tier,
        "overall_rank": family.get("overall_rank"),
        "top_next_run_rank": replay.get("top_next_run_rank"),
        "rolling_gate_status": family.get("rolling_gate_status", rolling.get("status", "not_in_rolling_gate")),
        "rolling_gate_repeat_live_win_count": int(family.get("rolling_gate_repeat_live_win_count", rolling.get("repeat_live_win_count", 0)) or 0),
        "rolling_gate_distinct_run_hash_count": int(
            family.get("rolling_gate_distinct_run_hash_count", rolling.get("distinct_run_hash_count", 0)) or 0
        ),
        "rolling_gate_source_count": int(family.get("rolling_gate_source_count", rolling.get("source_count", 0)) or 0),
        "natural_logic": family.get("natural_logic", ""),
        "benchmark_hypothesis": family.get("benchmark_hypothesis", ""),
        "baseline_contract": {
            "named_baseline": replay.get("named_baseline", ""),
            "baselines": family.get("baselines", []),
            "metrics": family.get("metrics", []),
            "promotion_metric": family.get("promotion_metric", ""),
        },
        "live_evidence": {
            "source_count": len(sources) or int(rolling.get("source_count", 0) or 0),
            "sources": sources,
            "snapshot_chain_sha256": replay_summary.get("snapshot_chain_sha256", rolling.get("upstream_snapshot_chain_sha256", "")),
            "unique_snapshot_sha256_count": replay_summary.get("unique_snapshot_sha256_count", 0),
        },
        "replay_result": result,
        "value_posture": {
            "safe_annual_value_surface_usd": family.get("safe_annual_value_surface_usd", 0.0),
            "blocked_context_annual_value_surface_usd": family.get("blocked_context_annual_value_surface_usd", 0.0),
            "ready_for_real_dollar_claim": False,
        },
        "claim_gate": {
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "field_validation": False,
            "kraken_live_execution_allowed": False,
            "boundary": BOUNDARY,
        },
        "allowed_language": allowed_language(tier, family or {"family_id": family_id}),
        "blocked_language": BLOCKED_LANGUAGE,
        "next_validation_steps": next_steps(tier, family),
    }
    card["card_sha256"] = sha256_payload(card)
    return card


def ordered_candidate_ids(queue: dict[str, Any], replay: dict[str, Any], champions: dict[str, Any], rolling: dict[str, Any]) -> list[str]:
    ids: list[str] = []

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if text and text not in ids:
            ids.append(text)

    for card in replay.get("replay_cards", []):
        if isinstance(card, dict):
            add(card.get("candidate_family_id"))
    for row in queue.get("champions", {}).get("triple_source_candidates", []):
        if isinstance(row, dict):
            add(row.get("family_id"))
    for row in queue.get("top_next_runs", [])[:8]:
        if isinstance(row, dict):
            add(row.get("family_id"))
    category = champions.get("category_champions", {}) if isinstance(champions.get("category_champions"), dict) else {}
    for key in ("top_family_asset", "proof_value_champion", "strict_triple_source_candidate", "strict_single_run_candidate"):
        row = category.get(key, {})
        if isinstance(row, dict):
            add(row.get("family"))
    for row in rolling.get("promotion_board", []):
        if isinstance(row, dict) and row.get("status") in {"triple_source_candidate", "single_run_candidate"}:
            add(row.get("family_id"))
    return ids


def build_payload() -> dict[str, Any]:
    queue = read_json(QUEUE_JSON)
    replay = read_json(REPLAY_JSON)
    champions = read_json(CHAMPIONS_JSON)
    rolling = read_json(ROLLING_JSON)

    families = index_by(queue.get("family_queue", []), "family_id")
    replay_cards = index_by(replay.get("replay_cards", []), "candidate_family_id")
    rolling_rows = index_by(rolling.get("promotion_board", []), "family_id")
    replay_summary = replay.get("summary", {}) if isinstance(replay.get("summary"), dict) else {}

    cards = []
    annex_cards = []
    for family_id in ordered_candidate_ids(queue, replay, champions, rolling):
        family = families.get(family_id, {})
        card = card_from_family(family_id, family, replay_cards.get(family_id, {}), rolling_rows.get(family_id, {}), replay_summary)
        if card["registry_family"]:
            cards.append(card)
        else:
            card["readiness_tier"] = f"external_rolling_candidate_not_registry_family::{card['readiness_tier']}"
            card["allowed_language"] = "Allowed: external rolling-gate candidate; add it to a formal registry lane before geometry claims."
            card["card_sha256"] = sha256_payload(card)
            annex_cards.append(card)

    cards.sort(
        key=lambda row: (
            0 if row["rolling_gate_status"] == "triple_source_candidate" else 1 if row["rolling_gate_status"] == "single_run_candidate" else 2,
            int(row["top_next_run_rank"] or 9999),
            int(row["overall_rank"] or 9999),
            row["family_id"],
        )
    )
    all_cards = cards + annex_cards
    card_chain = hashlib.sha256("\n".join(card["card_sha256"] for card in all_cards).encode("utf-8")).hexdigest()
    return {
        "generated_utc": now_utc(),
        "schema": "geometry_proof_card_pack_v1",
        "purpose": "Package top geometry and adjacent rolling-gate candidates into reviewer-safe proof cards.",
        "evidence_boundary": BOUNDARY,
        "summary": {
            "proof_card_count": len(all_cards),
            "registry_card_count": len(cards),
            "annex_card_count": len(annex_cards),
            "strict_rolling_champion_count": sum(1 for card in all_cards if card["rolling_gate_status"] == "rolling_champion"),
            "triple_source_candidate_count": sum(1 for card in all_cards if card["rolling_gate_status"] == "triple_source_candidate"),
            "single_run_candidate_count": sum(1 for card in all_cards if card["rolling_gate_status"] == "single_run_candidate"),
            "candidate_win_card_count": sum(1 for card in all_cards if card["replay_result"]["candidate_beats_named_baseline"] is True),
            "candidate_failed_or_context_only_count": sum(
                1 for card in all_cards if card["replay_result"]["candidate_beats_named_baseline"] is not True
            ),
            "card_chain_sha256": card_chain,
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "field_validation": False,
            "kraken_live_execution_allowed": False,
        },
        "proof_cards": all_cards,
        "inputs": {
            "geometry_live_breadth_proof_queue": str(QUEUE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "top_geometry_live_replay_results": str(REPLAY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_champion_of_champions": str(CHAMPIONS_JSON.relative_to(ROOT)).replace("\\", "/"),
            "rolling_champion_gate": str(ROLLING_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Proof Card Pack",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Summary",
        "",
        f"- Proof cards: `{summary['proof_card_count']}`",
        f"- Registry cards: `{summary['registry_card_count']}`",
        f"- Annex cards: `{summary['annex_card_count']}`",
        f"- Triple-source candidates: `{summary['triple_source_candidate_count']}`",
        f"- Single-run candidates: `{summary['single_run_candidate_count']}`",
        f"- Candidate win cards: `{summary['candidate_win_card_count']}`",
        f"- Card chain SHA-256: `{summary['card_chain_sha256']}`",
        f"- Ready for live geometry claim: `{str(summary['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        "",
        "## Cards",
        "",
        "| Family | Lane | Tier | Rolling Gate | Delta | Best Geometry | Card Hash |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for card in payload["proof_cards"]:
        result = card["replay_result"]
        delta = result["candidate_score_delta_vs_named_baseline"]
        delta_text = "n/a" if delta is None else str(delta)
        lines.append(
            f"| `{card['family_id']}` | `{card['lane']}` | `{card['readiness_tier']}` | "
            f"`{card['rolling_gate_status']}` | {delta_text} | `{result['best_geometry_family_id'] or 'n/a'}` | "
            f"`{card['card_sha256'][:12]}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["evidence_boundary"],
            "",
            "## Blocked Language",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in BLOCKED_LANGUAGE)
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "proof_cards": payload["summary"]["proof_card_count"],
                "triple_source_candidates": payload["summary"]["triple_source_candidate_count"],
                "single_run_candidates": payload["summary"]["single_run_candidate_count"],
                "ready_for_live_geometry_claim": payload["summary"]["ready_for_live_geometry_claim"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
