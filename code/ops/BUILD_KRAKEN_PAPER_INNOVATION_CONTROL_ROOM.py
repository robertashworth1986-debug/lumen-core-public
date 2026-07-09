from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT = ROOT / "out"
OUT_OPS = OUT / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

GLOBAL_RUNTIME = CONFIG / "runtime_control.json"
KRAKEN_RUNTIME = CONFIG / "accounts" / "KRAKEN_PRIMARY" / "runtime_control.json"
EXECUTION_STATUS = OUT / "execution_status.json"
ALPHA_MAP = OUT_OPS / "kraken_multi_tf_alpha_map_latest.json"
TRADING_AUDIT = OUT_OPS / "trading_stack_safety_audit_latest.json"
AUTONOMOUS_GOVERNANCE = OUT_OPS / "autonomous_quant_governance_packet_latest.json"

OUT_JSON = OUT_OPS / "kraken_paper_innovation_control_room_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "kraken_paper_innovation_control_room.json"
OUT_MD = DOCS / "KRAKEN_PAPER_INNOVATION_CONTROL_ROOM_2026-07-09.md"

SENSITIVE_MARKERS = [
    "password",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


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
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "live", "enabled"}
    return False


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def runtime_snapshot(
    global_runtime: dict[str, Any],
    kraken_runtime: dict[str, Any],
    execution_status: dict[str, Any],
    trading_audit: dict[str, Any],
) -> dict[str, Any]:
    global_mode = str(global_runtime.get("mode") or global_runtime.get("runtime_mode") or "").lower()
    account_mode = str(kraken_runtime.get("mode") or kraken_runtime.get("account_execution_mode") or "").lower()
    return {
        "global": {
            "mode": global_mode,
            "paper_enabled": truthy(global_runtime.get("paper_enabled")),
            "allow_live_orders": truthy(global_runtime.get("allow_live_orders")),
            "kill_switch": truthy(global_runtime.get("kill_switch")),
            "max_notional_per_trade_usd": safe_float(global_runtime.get("max_notional_per_trade_usd")),
            "max_daily_loss_usd": safe_float(global_runtime.get("max_daily_loss_usd")),
            "max_open_positions": int(safe_float(global_runtime.get("max_open_positions"))),
        },
        "kraken_account": {
            "account_id": str(kraken_runtime.get("account_id") or "KRAKEN_PRIMARY"),
            "mode": account_mode,
            "paper_enabled": truthy(kraken_runtime.get("paper_enabled")),
            "allow_live_orders": truthy(kraken_runtime.get("allow_live_orders")),
            "inherits_global_live_gate": truthy(kraken_runtime.get("inherits_global_live_gate")),
            "universe_executable_count": int(safe_float(kraken_runtime.get("universe_executable_count"))),
            "universe_shadow_count": int(safe_float(kraken_runtime.get("universe_shadow_count"))),
        },
        "execution_status": {
            "execution_mode": str(execution_status.get("execution_mode") or "").lower(),
            "live_arm": str(execution_status.get("live_arm") or "").upper(),
            "note": str(execution_status.get("note") or ""),
        },
        "trading_audit": {
            "posture": str(trading_audit.get("posture") or ""),
            "blockers": list(trading_audit.get("blockers") or []),
            "warnings": list(trading_audit.get("warnings") or []),
        },
    }


def research_mode_for(row: dict[str, Any]) -> str:
    strategy = str(row.get("strategy_mode") or "watch")
    if strategy == "momentum_snipe":
        return "paper_momentum_confirmation"
    if strategy == "mean_reversion_snapback":
        return "paper_reversion_decay_test"
    if strategy == "trend_follow_swing":
        return "paper_trend_persistence_test"
    return "paper_watch_only"


def risk_notes_for(row: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    spread_bps = safe_float(row.get("spread_bps"))
    turnover = safe_float(row.get("turnover_24h_usd"))
    range_24h = safe_float(row.get("range_24h_pct"))
    change_24h = safe_float(row.get("change_24h_pct"))
    if spread_bps > 25.0:
        notes.append("wide_spread_replay_only")
    if turnover < 1_000_000:
        notes.append("lower_turnover_size_cap_required")
    if range_24h > 40.0:
        notes.append("high_intraday_range_requires_slippage_stress")
    if abs(change_24h) > 20.0:
        notes.append("large_24h_move_requires_no_chase_rule")
    if not notes:
        notes.append("standard_paper_gate")
    return notes


def build_research_cards(alpha_map: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    leaders = alpha_map.get("alpha_leaderboard") if isinstance(alpha_map.get("alpha_leaderboard"), list) else []
    cards = []
    for rank, row in enumerate(leaders[:limit], start=1):
        if not isinstance(row, dict):
            continue
        card = {
            "rank": rank,
            "pair": row.get("pair"),
            "wsname": row.get("wsname"),
            "strategy_mode": row.get("strategy_mode"),
            "paper_research_mode": research_mode_for(row),
            "alpha_edge_score": safe_float(row.get("alpha_edge_score")),
            "momentum_score": safe_float(row.get("momentum_score")),
            "trend_score": safe_float(row.get("trend_score")),
            "reversion_score": safe_float(row.get("reversion_score")),
            "spread_bps": safe_float(row.get("spread_bps")),
            "turnover_24h_usd": safe_float(row.get("turnover_24h_usd")),
            "range_24h_pct": safe_float(row.get("range_24h_pct")),
            "change_24h_pct": safe_float(row.get("change_24h_pct")),
            "best_replay_entry_hour_utc": int(safe_float(row.get("best_buy_hour_utc"), -1)),
            "best_replay_exit_hour_utc": int(safe_float(row.get("best_sell_hour_utc"), -1)),
            "allowed_next_step": "paper_replay_ticket_only",
            "blocked_next_steps": [
                "no_live_order",
                "no_private_api_order",
                "no_position_size_change",
                "no_capital_movement",
            ],
            "risk_notes": risk_notes_for(row),
        }
        card["research_card_sha256"] = stable_sha256(card)
        cards.append(card)
    return cards


def build_payload() -> dict[str, Any]:
    global_runtime = read_json(GLOBAL_RUNTIME)
    kraken_runtime = read_json(KRAKEN_RUNTIME)
    execution_status = read_json(EXECUTION_STATUS)
    alpha_map = read_json(ALPHA_MAP)
    trading_audit = read_json(TRADING_AUDIT)
    governance = read_json(AUTONOMOUS_GOVERNANCE)

    snapshot = runtime_snapshot(global_runtime, kraken_runtime, execution_status, trading_audit)
    cards = build_research_cards(alpha_map)
    global_paper = snapshot["global"]["mode"] == "paper" and snapshot["global"]["paper_enabled"]
    account_paper = snapshot["kraken_account"]["mode"] == "paper" and snapshot["kraken_account"]["paper_enabled"]
    live_disabled = (
        snapshot["global"]["allow_live_orders"] is False
        and snapshot["kraken_account"]["allow_live_orders"] is False
        and snapshot["execution_status"]["live_arm"] in {"OFF", ""}
    )
    audit_blocks_live = snapshot["trading_audit"]["posture"] != "PAPER_OK" or bool(snapshot["trading_audit"]["blockers"])
    status_ready = bool(cards) and global_paper and account_paper and live_disabled

    payload = {
        "schema": "kraken_paper_innovation_control_room_v1",
        "generated_utc": now_utc(),
        "status": "KRAKEN_PAPER_INNOVATION_READY_LIVE_BLOCKED" if status_ready else "KRAKEN_PAPER_INNOVATION_BLOCKED",
        "summary": {
            "public_alpha_map_present": bool(alpha_map),
            "paper_research_card_count": len(cards),
            "pairs_discovered": int(safe_float(alpha_map.get("pairs_discovered"))),
            "pairs_after_liquidity_filter": int(safe_float(alpha_map.get("pairs_after_liquidity_filter"))),
            "pairs_analyzed": int(safe_float(alpha_map.get("pairs_analyzed"))),
            "pair_errors": int(safe_float(alpha_map.get("pair_errors"))),
            "global_runtime_paper": global_paper,
            "kraken_runtime_paper": account_paper,
            "global_live_orders_disabled": snapshot["global"]["allow_live_orders"] is False,
            "kraken_live_orders_disabled": snapshot["kraken_account"]["allow_live_orders"] is False,
            "live_arm_off": snapshot["execution_status"]["live_arm"] in {"OFF", ""},
            "trading_audit_posture": snapshot["trading_audit"]["posture"],
            "trading_audit_blocker_count": len(snapshot["trading_audit"]["blockers"]),
            "live_promotion_blocked": True,
            "private_api_use_allowed_without_human": False,
            "validate_only_allowed_without_action_time_approval": False,
            "order_placement_allowed": False,
            "capital_movement_allowed": False,
            "keys_loaded_by_this_packet": False,
        },
        "runtime_snapshot": snapshot,
        "paper_research_cards": cards,
        "innovation_protocol": {
            "allowed_now": [
                "public Kraken market scans",
                "paper replay tickets",
                "watchlist scoring",
                "spread and slippage stress tests",
                "validate-only smoke-test planning without secrets",
            ],
            "blocked_now": [
                "private endpoint calls without action-time approval",
                "live orders",
                "auto-fire",
                "withdrawals",
                "collateral conversion",
                "position-size escalation",
                "profit or return promises",
            ],
            "promotion_requirements": [
                "fresh executor heartbeat",
                "fresh autofire heartbeat",
                "growth controller health OK",
                "zero trading audit blockers",
                "paper replay receipt for selected pair",
                "validate-only smoke test explicitly approved by human",
                "separate human action-time approval for any live order",
            ],
        },
        "key_policy": {
            "registry_note": "Keys may exist in the local registry, but this packet does not read, print, hydrate, or use them.",
            "secret_handling": "Private credentials stay outside the control-room artifact. Any key verification must report presence only and never display secret values.",
            "safe_next_private_step": "Only a human-approved validate-only smoke test with validate=true may use private credentials before any live path is considered.",
        },
        "source_artifacts": [
            artifact_status(GLOBAL_RUNTIME),
            artifact_status(KRAKEN_RUNTIME),
            artifact_status(EXECUTION_STATUS),
            artifact_status(ALPHA_MAP),
            artifact_status(TRADING_AUDIT),
            artifact_status(AUTONOMOUS_GOVERNANCE),
        ],
        "source_governance_status": str(governance.get("status") or ""),
        "claim_boundary": [
            "Research cards are not investment advice.",
            "Scores are public-market research signals, not buy/sell instructions.",
            "No live trading, order placement, capital movement, account change, or private API use is authorized by this packet.",
            "No performance, profit, or guaranteed-safety claim is made.",
        ],
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["kraken_paper_innovation_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Kraken Paper Innovation Control Room - 2026-07-09",
        "",
        "Purpose: connect Kraken market evidence to LumenCore's paper/replay innovation loop while keeping private credentials, live orders, and capital movement outside the automation boundary.",
        "",
        "This packet is not investment advice and does not authorize trading.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Public alpha map present: `{str(summary['public_alpha_map_present']).lower()}`",
        f"- Paper research cards: `{summary['paper_research_card_count']}`",
        f"- Pairs discovered: `{summary['pairs_discovered']}`",
        f"- Pairs after liquidity filter: `{summary['pairs_after_liquidity_filter']}`",
        f"- Pairs analyzed: `{summary['pairs_analyzed']}`",
        f"- Pair errors: `{summary['pair_errors']}`",
        f"- Global runtime paper: `{str(summary['global_runtime_paper']).lower()}`",
        f"- Kraken runtime paper: `{str(summary['kraken_runtime_paper']).lower()}`",
        f"- Global live orders disabled: `{str(summary['global_live_orders_disabled']).lower()}`",
        f"- Kraken live orders disabled: `{str(summary['kraken_live_orders_disabled']).lower()}`",
        f"- Live arm off: `{str(summary['live_arm_off']).lower()}`",
        f"- Trading audit posture: `{summary['trading_audit_posture']}`",
        f"- Trading audit blockers: `{summary['trading_audit_blocker_count']}`",
        f"- Live promotion blocked: `{str(summary['live_promotion_blocked']).lower()}`",
        f"- Private API use without human: `{str(summary['private_api_use_allowed_without_human']).lower()}`",
        f"- Validate-only without action-time approval: `{str(summary['validate_only_allowed_without_action_time_approval']).lower()}`",
        f"- Order placement allowed: `{str(summary['order_placement_allowed']).lower()}`",
        f"- Capital movement allowed: `{str(summary['capital_movement_allowed']).lower()}`",
        f"- Keys loaded by this packet: `{str(summary['keys_loaded_by_this_packet']).lower()}`",
        f"- Packet SHA-256: `{payload['kraken_paper_innovation_sha256']}`",
        "",
        "## Paper Research Cards",
        "",
    ]
    for card in payload["paper_research_cards"]:
        lines.extend(
            [
                f"### {card['rank']}. {card['wsname'] or card['pair']}",
                "",
                f"- Pair: `{card['pair']}`",
                f"- Strategy mode: `{card['strategy_mode']}`",
                f"- Paper research mode: `{card['paper_research_mode']}`",
                f"- Alpha edge score: `{card['alpha_edge_score']}`",
                f"- Momentum / trend / reversion: `{card['momentum_score']}` / `{card['trend_score']}` / `{card['reversion_score']}`",
                f"- Spread bps: `{card['spread_bps']}`",
                f"- 24h turnover USD: `{card['turnover_24h_usd']}`",
                f"- 24h range pct: `{card['range_24h_pct']}`",
                f"- 24h change pct: `{card['change_24h_pct']}`",
                f"- Replay entry hour UTC: `{card['best_replay_entry_hour_utc']}`",
                f"- Replay exit hour UTC: `{card['best_replay_exit_hour_utc']}`",
                f"- Allowed next step: `{card['allowed_next_step']}`",
                f"- Blocked next steps: `{', '.join(card['blocked_next_steps'])}`",
                f"- Risk notes: `{', '.join(card['risk_notes'])}`",
                f"- Card SHA-256: `{card['research_card_sha256']}`",
                "",
            ]
        )

    protocol = payload["innovation_protocol"]
    lines.extend(["## Innovation Protocol", "", "Allowed now:"])
    for item in protocol["allowed_now"]:
        lines.append(f"- {item}")
    lines.extend(["", "Blocked now:"])
    for item in protocol["blocked_now"]:
        lines.append(f"- {item}")
    lines.extend(["", "Promotion requirements:"])
    for item in protocol["promotion_requirements"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Key Policy", ""])
    for key, value in payload["key_policy"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Source Artifacts", ""])
    for row in payload["source_artifacts"]:
        lines.append(
            f"- `{row['path']}` present=`{str(row['present']).lower()}` bytes=`{row['bytes']}` sha256=`{row['sha256']}`"
        )

    lines.extend(["", "## Claim Boundary", ""])
    for item in payload["claim_boundary"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> int:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive Kraken control-room markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "paper_research_cards": payload["summary"]["paper_research_card_count"],
                "live_promotion_blocked": payload["summary"]["live_promotion_blocked"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"] == "KRAKEN_PAPER_INNOVATION_READY_LIVE_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
