from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

OUT_JSON = OUT_OPS / "luma_operator_context_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "luma_operator_context.json"
OUT_MD = DOCS / "LUMA_OPERATOR_CONTEXT_2026-07-01.md"

BOUNDARY = (
    "Continuity and operator context artifact. It consolidates current proof, source, deployment, "
    "claim, and outreach state so future passes start from the same truth. It does not authorize "
    "bulk outreach, external submissions, live trading, field-validation language, realized-savings "
    "claims, medical claims, or fixed dollar pricing for frozen deltas."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")
    os.replace(temporary, path)


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def load_inputs() -> dict[str, dict[str, Any]]:
    return {
        "champion_metric_gauntlet": read_json(DASHBOARD_DATA / "champion_metric_gauntlet.json"),
        "champion_expanded_metric_rollup": read_json(DASHBOARD_DATA / "champion_expanded_metric_rollup.json"),
        "locked_source_baseline_replay_sweep": read_json(DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"),
        "geometry_ready_source_replay": read_json(DASHBOARD_DATA / "geometry_ready_source_replay.json"),
        "geometry_live_wiring_matrix": read_json(DASHBOARD_DATA / "geometry_live_wiring_matrix.json"),
        "live_domain_deployment_feed": read_json(DASHBOARD_DATA / "live_domain_deployment_feed.json"),
        "live_domain_proof_feed_deploy_bundle": read_json(DASHBOARD_DATA / "live_domain_proof_feed_deploy_bundle.json"),
        "dollar_claim_gate": read_json(DASHBOARD_DATA / "dollar_claim_gate.json"),
        "field_validated_dollar_claim_ladder": read_json(DASHBOARD_DATA / "field_validated_dollar_claim_ladder.json"),
        "first_buyer_target_board": read_json(DASHBOARD_DATA / "first_buyer_target_board.json"),
        "safe_key_provider_ping": read_json(DASHBOARD_DATA / "safe_key_provider_ping.json"),
        "live_key_measurement_audit": read_json(OUT_OPS / "live_key_measurement_audit_latest.json"),
        "live_source_measurement_maximizer": read_json(DASHBOARD_DATA / "live_source_measurement_maximizer.json"),
        "live_evidence_max_harvest": read_json(DASHBOARD_DATA / "live_evidence_max_harvest.json"),
    }


def provider_gap_rows(provider_ping: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in as_list(provider_ping.get("provider_rows")):
        provider = as_dict(row)
        status = as_dict(provider.get("latest_status"))
        status_name = str(status.get("status") or "NO_LATEST_STATUS")
        key_ready = bool(provider.get("key_ready"))
        if key_ready and status_name == "MEASURED":
            continue
        rows.append(
            {
                "source": provider.get("source"),
                "sector": provider.get("sector"),
                "enabled": bool(provider.get("enabled")),
                "key_ready": key_ready,
                "missing_env_names": provider.get("missing_env_names") or [],
                "latest_status": status_name,
                "http_status": status.get("http_status"),
                "safe_next_action": provider_next_action(provider),
            }
        )
    return rows


def provider_next_action(provider: dict[str, Any]) -> str:
    source = str(provider.get("source") or "")
    status = as_dict(provider.get("latest_status"))
    note = str(status.get("probe_note") or "").lower()
    if not provider.get("enabled"):
        return "Enable only if this source is needed for the current proof lane, then bind the expected API key."
    if not provider.get("key_ready"):
        return "Bind the missing API key names in the local env file or registry, then rerun safe provider ping."
    if source == "BINANCE_PUBLIC":
        return "Do not fight the location restriction; use Kraken/CoinGecko or another allowed market source instead."
    if source == "EIA":
        return "Rerun the EIA probe and promote existing local EIA CSV/API pulls; 502 appears upstream, not proof failure."
    if source == "EPA_AQS":
        return "Refresh the EPA AQS email/key pair; the latest probe reports invalid email/key."
    if source == "NASA" and "timeout" in note:
        return "Rerun with a longer timeout and a smaller endpoint before declaring NASA unavailable."
    if source == "NREL":
        return "Retry DNS/network and use a known NREL developer endpoint; current failure is name resolution."
    if source == "THE_ODDS_API":
        return "Reactivate or replace the key before using sports-market data in current proof claims."
    if status == {}:
        return "Add this provider to the latest safe ping/harvest adapter so key-ready becomes measured, not merely configured."
    return "Review the redacted probe note, repair the adapter or key, then rerun the provider harvest."


def lane_scoreboard(sweep: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in as_list(sweep.get("lane_scoreboard")):
        lane = as_dict(row)
        comparisons = int(lane.get("baseline_comparison_count") or 0)
        wins = int(lane.get("candidate_win_count") or 0)
        rows.append(
            {
                "lane": lane.get("lane"),
                "evidence_mode": lane.get("evidence_mode"),
                "candidate_win_count": wins,
                "baseline_comparison_count": comparisons,
                "win_rate": round(wins / comparisons, 6) if comparisons else 0.0,
                "estimated_rows": lane.get("estimated_rows"),
                "numeric_samples": lane.get("numeric_samples"),
                "routes_replayed": lane.get("routes_replayed"),
                "mean_score_delta": lane.get("mean_score_delta"),
                "best_score_delta": lane.get("best_score_delta"),
                "global_holm_positive_count": int(
                    lane.get("global_holm_positive_count") or 0
                ),
                "source_names": lane.get("source_names") or [],
                "locked_baselines": lane.get("locked_baselines") or [],
                "metric_names": lane.get("metric_names") or [],
            }
        )
    return rows


def next_metric_battery(champion: dict[str, Any]) -> list[dict[str, Any]]:
    battery: list[dict[str, Any]] = []
    for row in as_list(champion.get("metric_expansion_suite")):
        suite = as_dict(row)
        battery.append(
            {
                "family_id": suite.get("family_id"),
                "status": suite.get("status"),
                "target_question": suite.get("target_question"),
                "metrics": suite.get("metrics") or [],
                "next_action": suite.get("next_action"),
                "claim_gate": suite.get("claim_gate"),
            }
        )
    return battery


def outreach_snapshot(board: dict[str, Any]) -> dict[str, Any]:
    summary = as_dict(board.get("summary"))
    candidates = [as_dict(row) for row in as_list(board.get("candidates"))]
    primary = as_dict(board.get("primary_manual_email"))
    first = candidates[0] if candidates else {}
    return {
        "recommended_first_buyer": summary.get("recommended_first_buyer"),
        "recommended_first_action": summary.get("recommended_first_action"),
        "paid_protocol_review_scoping_allowed": bool(
            summary.get("paid_protocol_review_scoping_allowed")
        ),
        "manual_reviewed_outreach_allowed": bool(summary.get("manual_reviewed_outreach_allowed")),
        "send_without_user_review_allowed": bool(summary.get("send_without_user_review_allowed")),
        "top_contact_lane": {
            "organization": first.get("organization"),
            "fit_score": first.get("fit_score"),
            "buyer_channel_type": first.get("buyer_channel_type"),
            "first_ask": first.get("first_ask"),
            "routing_status": first.get("routing_status"),
            "send_now_allowed": bool(first.get("send_now_allowed")),
            "source_refs": first.get("source_refs") or [],
        },
        "manual_email_subject": primary.get("subject"),
        "manual_email_body": primary.get("body"),
        "send_gate": (
            "No send is authorized. Verify the current official channel, reconcile "
            "duplicate-send history, select a real recipient, and obtain exact "
            "action-time approval."
        ),
    }


def build_payload() -> dict[str, Any]:
    inputs = load_inputs()
    required_schemas = {
        "champion_metric_gauntlet": "champion_metric_gauntlet_v2",
        "champion_expanded_metric_rollup": "champion_expanded_metric_rollup_v2",
        "locked_source_baseline_replay_sweep": "locked_source_baseline_replay_sweep_v2",
        "geometry_ready_source_replay": "geometry_ready_source_replay_v2",
        "geometry_live_wiring_matrix": "geometry_live_wiring_matrix_v3",
        "first_buyer_target_board": "first_buyer_target_board_v2",
    }
    for name, expected in required_schemas.items():
        actual = inputs[name].get("schema")
        if actual != expected:
            raise ValueError(f"{name} must use {expected}; found {actual!r}")

    champion = inputs["champion_metric_gauntlet"]
    champion_summary = as_dict(champion.get("summary"))
    strongest = as_dict(champion.get("strongest_current"))
    expanded = inputs["champion_expanded_metric_rollup"]
    expanded_summary = as_dict(expanded.get("summary")) or expanded
    sweep_summary = as_dict(
        inputs["locked_source_baseline_replay_sweep"].get("summary")
    )
    wiring_summary = as_dict(inputs["geometry_live_wiring_matrix"].get("summary"))
    domain_summary = as_dict(inputs["live_domain_deployment_feed"].get("summary"))
    bundle_summary = as_dict(inputs["live_domain_proof_feed_deploy_bundle"].get("summary"))
    dollar_summary = as_dict(inputs["dollar_claim_gate"].get("summary"))
    key_summary = as_dict(inputs["live_key_measurement_audit"].get("summary"))
    safe_key_summary = as_dict(inputs["safe_key_provider_ping"].get("summary"))
    source_summary = as_dict(inputs["live_source_measurement_maximizer"].get("summary"))
    harvest_summary = as_dict(inputs["live_evidence_max_harvest"].get("summary"))

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "luma_operator_context_v2",
        "purpose": "Anti-drift memory and execution board for LumenCore proof-to-pilot work.",
        "boundary": BOUNDARY,
        "truth_state": {
            "internal_performance_champion_present": False,
            "current_champion": None,
            "measured_reference_candidate": champion_summary.get("champion_family"),
            "measured_reference_label": champion_summary.get("champion_label"),
            "development_selected_candidate": strongest.get(
                "development_selected_candidate"
            ),
            "candidate_was_protocol_selected": bool(
                strongest.get("candidate_was_protocol_selected")
            ),
            "named_baseline": champion_summary.get("named_baseline"),
            "holdout_wins": champion_summary.get("holdout_wins"),
            "holdout_count": champion_summary.get("holdout_count"),
            "win_rate": champion_summary.get("holdout_win_rate"),
            "mean_delta_vs_named_baseline": champion_summary.get("mean_delta_vs_named_baseline"),
            "min_delta_vs_named_baseline": champion_summary.get("min_delta_vs_named_baseline"),
            "estimated_rows_replayed": champion_summary.get("estimated_rows_replayed"),
            "source_system_count": champion_summary.get("source_system_count"),
            "source_systems": strongest.get("source_systems") or [],
            "registered_baseline_count": strongest.get("registered_baseline_count"),
            "registered_baseline_mean_win_count": strongest.get(
                "registered_baseline_mean_win_count"
            ),
            "candidate_beats_all_registered_baselines_after_holm": bool(
                strongest.get("candidate_beats_all_registered_baselines_after_holm")
            ),
            "compatibility_route_count": expanded_summary.get("route_count"),
            "direct_measured_route_count": expanded_summary.get(
                "direct_measured_route_count"
            ),
            "conditioned_synthetic_route_count": expanded_summary.get(
                "conditioned_synthetic_route_count"
            ),
            "baseline_comparison_count": expanded_summary.get(
                "baseline_comparison_count"
            ),
            "raw_candidate_win_count": sweep_summary.get("candidate_win_count"),
            "direct_all_baseline_global_holm_positive_count": expanded_summary.get(
                "global_holm_positive_count"
            ),
            "performance_rows_reviewed": expanded_summary.get(
                "performance_rows_reviewed"
            ),
            "legacy_ready_rows_excluded": expanded_summary.get(
                "legacy_rows_excluded"
            ),
            "numeric_fallback_count": expanded_summary.get(
                "numeric_fallback_count"
            ),
            "geometry_inventory_measured_source_count": wiring_summary.get(
                "live_source_measured_count"
            ),
            "geometry_inventory_measured_row_count": wiring_summary.get(
                "total_measured_rows"
            ),
            "geometry_inventory_is_performance_evidence": False,
            "expanded_plain_english": expanded_summary.get("plain_english_answer"),
            "reviewer_safe_internal_claim_allowed": False,
            "reviewer_safe_measured_nonpromotion_claim_allowed": bool(
                champion_summary.get(
                    "reviewer_safe_measured_nonpromotion_claim_allowed"
                )
            ),
            "buyer_authorized_field_replay_request_ready": bool(
                champion_summary.get("buyer_authorized_field_replay_request_ready")
            ),
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
            "plain_english": champion_summary.get("plain_english_answer"),
        },
        "live_domain": {
            "state": domain_summary.get("domain_deployment_state"),
            "local_ready": bool(domain_summary.get("local_required_ready")),
            "reviewer_ready": bool(domain_summary.get("live_domain_reviewer_ready")),
            "required_feed_count": domain_summary.get("required_feed_count"),
            "required_remote_hash_match_count": domain_summary.get("required_remote_hash_match_count"),
            "required_remote_stale_or_missing_count": domain_summary.get("required_remote_stale_or_missing_count"),
            "feed_only_deploy_ready": bool(bundle_summary.get("feed_only_deploy_ready")),
            "safe_deploy_command": domain_summary.get("safe_deploy_command")
            or inputs["live_domain_deployment_feed"].get("safe_deploy_command"),
        },
        "source_breadth": {
            "runtime_bound_keys_total": key_summary.get("runtime_bound_keys_total"),
            "enabled_sources_total": key_summary.get("enabled_sources_total"),
            "measured_sources_total": key_summary.get("measured_sources_total"),
            "measured_coverage_pct": key_summary.get("measured_coverage_pct"),
            "enabled_sectors_total": key_summary.get("enabled_sectors_total"),
            "measured_sectors_total": key_summary.get("measured_sectors_total"),
            "fresh_http_enabled_sources_total": source_summary.get("enabled_sources"),
            "fresh_http_measured_sources_total": source_summary.get("measured_sources"),
            "fresh_http_failed_or_thin_sources_total": source_summary.get("failed_or_thin_sources"),
            "fresh_http_total_measured_rows": source_summary.get("total_measured_rows"),
            "fresh_http_coverage_pct": source_summary.get("coverage_pct"),
            "fresh_http_measured_source_names": source_summary.get("measured_source_names") or [],
            "fresh_http_failed_or_thin_source_names": source_summary.get("failed_or_thin_source_names") or [],
            "live_context_replay_rows_evaluated": harvest_summary.get("total_live_context_rows_evaluated"),
            "live_context_candidate_beats_named_baseline_count": harvest_summary.get(
                "candidate_beats_named_baseline_count"
            ),
            "live_context_snapshot_chain_sha256": harvest_summary.get("snapshot_chain_sha256"),
            "safe_ping_provider_count": safe_key_summary.get("provider_count"),
            "safe_ping_key_ready_provider_count": safe_key_summary.get("key_ready_provider_count"),
            "safe_ping_latest_measured_provider_count": safe_key_summary.get("latest_measured_provider_count"),
            "safe_ping_latest_blocked_or_thin_provider_count": safe_key_summary.get(
                "latest_blocked_or_thin_provider_count"
            ),
            "provider_gaps": provider_gap_rows(inputs["safe_key_provider_ping"]),
        },
        "locked_replay_lanes": lane_scoreboard(inputs["locked_source_baseline_replay_sweep"]),
        "metric_battery": next_metric_battery(champion),
        "dollar_gate": {
            "allowed_estimated_hourly_value_usd": dollar_summary.get("allowed_estimated_hourly_value_usd"),
            "allowed_estimated_annual_value_usd": dollar_summary.get("allowed_estimated_annual_value_usd"),
            "blocked_context_only_annual_value_usd": dollar_summary.get("blocked_context_only_annual_value_usd"),
            "realized_savings_allowed": False,
            "field_validation_required_for_real_dollars": True,
            "safe_line": (
                "The current priceable work is a bounded source-native benchmark "
                "and evidence protocol review. Realized savings require a future "
                "promoted candidate, buyer-authorized field replay, locked baseline, "
                "held-out data, accepted metric, and approved economic conversion."
            ),
        },
        "outreach": outreach_snapshot(inputs["first_buyer_target_board"]),
        "next_10_actions": [
            "Run the focused proof tests before every commit.",
            "Treat the 24-source geometry inventory as research capacity, not performance evidence.",
            "Keep Kuramoto as measured negative evidence; do not call it a champion.",
            "Select the next wave-family candidate on development data only.",
            "Register every source-native baseline before opening the untouched holdout.",
            "Require every baseline gate to pass after multiplicity correction.",
            "Keep live-domain hash verification green after every proof feed update.",
            "Offer only a bounded paid protocol review while no candidate is promoted.",
            "Do not open new EPRI outreach; that lane remains inbound-only.",
            "Require exact action-time approval before any external send.",
        ],
        "operator_prompt": (
            "Operate LumenCore as a measurement-first evidence and benchmark "
            "platform. The standard is reviewer-safe proof that survives hostile "
            "reading. Every comparison must name its source task, native units, "
            "registered baselines, chronology, metrics, multiplicity correction, "
            "code commit, hashes, negative results, and claim boundary. No current "
            "geometry family is a performance champion. Kuramoto is a useful direct "
            "measured negative result: it was not development-selected, won 482 of "
            "1,525 paired EIA days against the named Kalman baseline, and had mean "
            "skill delta -0.508191. Keep direct measured and conditioned-synthetic "
            "routes separate. Treat source breadth as adapter inventory. The "
            "commercially honest near-term offer is a bounded source-native protocol "
            "review or benchmark implementation, with no candidate-win, field, "
            "savings, or live-execution claim. Publish only canonical secret-free "
            "proof feeds, preserve failures, and require exact action-time approval "
            "for every external send."
        ),
    }
    payload["context_sha256"] = stable_sha256(
        {
            "truth_state": payload["truth_state"],
            "live_domain": payload["live_domain"],
            "source_breadth": payload["source_breadth"],
            "locked_replay_lanes": payload["locked_replay_lanes"],
            "dollar_gate": payload["dollar_gate"],
            "next_10_actions": payload["next_10_actions"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    truth = as_dict(payload.get("truth_state"))
    source_breadth = as_dict(payload.get("source_breadth"))
    live_domain = as_dict(payload.get("live_domain"))
    dollar_gate = as_dict(payload.get("dollar_gate"))
    outreach = as_dict(payload.get("outreach"))
    lines = [
        "# Luma Operator Context",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        f"Context SHA-256: `{payload.get('context_sha256')}`",
        "",
        "## Current Truth",
        "",
        f"- Internal performance champion present: `{str(truth.get('internal_performance_champion_present')).lower()}`",
        f"- Current performance champion: `{truth.get('current_champion') or 'none'}`",
        f"- Measured reference candidate: `{truth.get('measured_reference_candidate')}`",
        f"- Development-selected candidate: `{truth.get('development_selected_candidate')}`",
        f"- Reference candidate was protocol-selected: `{str(truth.get('candidate_was_protocol_selected')).lower()}`",
        f"- Named baseline: `{truth.get('named_baseline')}`",
        f"- Paired-day wins: `{truth.get('holdout_wins')}/{truth.get('holdout_count')}`",
        f"- Mean skill delta: `{truth.get('mean_delta_vs_named_baseline')}`",
        f"- Registered baseline mean wins: `{truth.get('registered_baseline_mean_win_count')}/{truth.get('registered_baseline_count')}`",
        f"- All-baseline Holm gate passed: `{str(truth.get('candidate_beats_all_registered_baselines_after_holm')).lower()}`",
        f"- Compatible routes: `{truth.get('compatibility_route_count')}`",
        f"- Direct measured routes: `{truth.get('direct_measured_route_count')}`",
        f"- Conditioned-synthetic routes: `{truth.get('conditioned_synthetic_route_count')}`",
        f"- Raw baseline comparison wins: `{truth.get('raw_candidate_win_count')}/{truth.get('baseline_comparison_count')}`",
        f"- Direct all-baseline global promotions: `{truth.get('direct_all_baseline_global_holm_positive_count')}`",
        f"- Performance rows reviewed: `{truth.get('performance_rows_reviewed')}`",
        f"- Legacy ready rows excluded: `{truth.get('legacy_ready_rows_excluded')}`",
        f"- Numeric fallbacks: `{truth.get('numeric_fallback_count')}`",
        f"- Geometry source inventory: `{truth.get('geometry_inventory_measured_source_count')}` measured sources / `{truth.get('geometry_inventory_measured_row_count')}` rows",
        f"- Geometry source inventory is performance evidence: `{str(truth.get('geometry_inventory_is_performance_evidence')).lower()}`",
        f"- Buyer field replay request ready: `{str(truth.get('buyer_authorized_field_replay_request_ready')).lower()}`",
        f"- Field validation claim allowed: `false`",
        f"- Real dollar savings claim allowed: `false`",
        "",
        str(truth.get("plain_english") or ""),
        "",
        str(truth.get("expanded_plain_english") or ""),
        "",
        "## Live Domain",
        "",
        f"- State: `{live_domain.get('state')}`",
        f"- Reviewer ready: `{str(live_domain.get('reviewer_ready')).lower()}`",
        f"- Required feeds matched: `{live_domain.get('required_remote_hash_match_count')}/{live_domain.get('required_feed_count')}`",
        f"- Stale/missing required feeds: `{live_domain.get('required_remote_stale_or_missing_count')}`",
        "",
        "## Source Breadth",
        "",
        f"- Runtime-bound keys: `{source_breadth.get('runtime_bound_keys_total')}`",
        f"- Measured enabled sources: `{source_breadth.get('measured_sources_total')}/{source_breadth.get('enabled_sources_total')}`",
        f"- Measured sectors: `{source_breadth.get('measured_sectors_total')}/{source_breadth.get('enabled_sectors_total')}`",
        f"- Fresh HTTP measured sources: `{source_breadth.get('fresh_http_measured_sources_total')}/{source_breadth.get('fresh_http_enabled_sources_total')}`",
        f"- Fresh HTTP measured rows: `{source_breadth.get('fresh_http_total_measured_rows')}`",
        f"- Live-context replay rows: `{source_breadth.get('live_context_replay_rows_evaluated')}`",
        f"- Live-context candidate wins vs named baselines: `{source_breadth.get('live_context_candidate_beats_named_baseline_count')}`",
        f"- Live-context snapshot chain: `{source_breadth.get('live_context_snapshot_chain_sha256')}`",
        f"- Latest measured providers in safe ping: `{source_breadth.get('safe_ping_latest_measured_provider_count')}`",
        f"- Latest blocked/thin providers in safe ping: `{source_breadth.get('safe_ping_latest_blocked_or_thin_provider_count')}`",
        "",
        "Provider gaps to fix:",
    ]
    for row in as_list(source_breadth.get("provider_gaps")):
        gap = as_dict(row)
        lines.append(
            f"- `{gap.get('source')}`: `{gap.get('latest_status')}`; next: {gap.get('safe_next_action')}"
        )

    lines.extend(
        [
            "",
            "## Replay Lanes",
            "",
            "| Lane | Evidence Mode | Wins | Comparisons | Global Holm Positive | Samples | Mean Delta |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in as_list(payload.get("locked_replay_lanes")):
        lane = as_dict(row)
        lines.append(
            "| "
            f"`{lane.get('lane')}` | "
            f"`{lane.get('evidence_mode')}` | "
            f"{lane.get('candidate_win_count')} | "
            f"{lane.get('baseline_comparison_count')} | "
            f"{lane.get('global_holm_positive_count')} | "
            f"{lane.get('numeric_samples')} | "
            f"{lane.get('mean_score_delta')} |"
        )

    lines.extend(
        [
            "",
            "## Dollar Gate",
            "",
            f"- Bounded estimated hourly signal: `${dollar_gate.get('allowed_estimated_hourly_value_usd')}`",
            f"- Bounded estimated annual signal: `${dollar_gate.get('allowed_estimated_annual_value_usd')}`",
            f"- Blocked context-only annual surface: `${dollar_gate.get('blocked_context_only_annual_value_usd')}`",
            f"- Safe line: {dollar_gate.get('safe_line')}",
            "",
            "## Protocol Review Lane",
            "",
            f"- Recommended buyer: `{outreach.get('recommended_first_buyer') or 'none'}`",
            f"- Action: {outreach.get('recommended_first_action')}",
            f"- Paid protocol-review scoping allowed: `{str(outreach.get('paid_protocol_review_scoping_allowed')).lower()}`",
            f"- Manual reviewed outreach allowed: `{str(outreach.get('manual_reviewed_outreach_allowed')).lower()}`",
            f"- Send gate: {outreach.get('send_gate')}",
            "",
            "## Next 10 Actions",
            "",
        ]
    )
    for action in as_list(payload.get("next_10_actions")):
        lines.append(f"- {action}")

    lines.extend(["", "## Long-Arc Operator Prompt", "", str(payload.get("operator_prompt") or "")])
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(payload["truth_state"]["plain_english"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
