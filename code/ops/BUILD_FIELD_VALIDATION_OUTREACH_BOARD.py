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

CONTROL_ROOM_JSON = OUT_OPS / "field_validation_control_room_latest.json"
GAUNTLET_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
FIRST_BUYER_JSON = DASHBOARD_DATA / "first_buyer_target_board.json"
VALUATION_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"
WIRING_JSON = DASHBOARD_DATA / "geometry_live_wiring_matrix.json"

OUT_JSON = OUT_OPS / "field_validation_outreach_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validation_outreach_board.json"
OUT_MD = DOCS / "FIELD_VALIDATION_OUTREACH_BOARD_2026-06-29.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


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


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def require_inputs() -> dict[str, dict[str, Any]]:
    inputs = {
        "control_room": read_json(CONTROL_ROOM_JSON),
        "gauntlet": read_json(GAUNTLET_JSON),
        "first_buyer": read_json(FIRST_BUYER_JSON),
        "valuation": read_json(VALUATION_JSON),
        "wiring": read_json(WIRING_JSON),
    }
    expected = {
        "control_room": "field_validation_control_room_v2",
        "gauntlet": "champion_metric_gauntlet_v2",
        "first_buyer": "first_buyer_target_board_v2",
        "valuation": "valuation_proposal_target_packet_v3",
        "wiring": "geometry_live_wiring_matrix_v3",
    }
    for name, schema in expected.items():
        actual = inputs[name].get("schema")
        if actual != schema:
            raise ValueError(f"{name} must use {schema}; found {actual!r}")
    return inputs


def bounded_targets(first_buyer: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in as_list(first_buyer.get("candidates")):
        row = as_dict(candidate)
        if not row:
            continue
        routing = str(row.get("routing_status") or "")
        if routing == "inbound_only_no_new_outreach":
            next_action = (
                "Monitor the existing inbound-only channel. Do not send a new inquiry."
            )
        else:
            next_action = (
                "Treat this as a historical research candidate only. Verify a "
                "current official route, reconcile duplicate-send history, select "
                "a real recipient, and obtain exact action-time approval before "
                "drafting or sending anything."
            )
        bounded = {
            "rank": row.get("rank"),
            "organization": row.get("organization"),
            "fit_score": row.get("fit_score"),
            "buyer_channel_type": row.get("buyer_channel_type"),
            "routing_status": routing,
            "source_freshness_status": row.get("source_freshness_status"),
            "send_now_allowed": False,
            "manual_review_required": True,
            "protocol_review_fit": row.get("proof_fit") or [],
            "safe_proof_line": row.get("proof_line", ""),
            "safe_first_ask": (
                "After current-route verification, ask only whether a bounded "
                "source-native benchmark and evidence protocol review fits the "
                "organization's current technical program."
            ),
            "safe_next_action": next_action,
        }
        bounded["target_sha256"] = stable_sha256(bounded)
        rows.append(bounded)
    return rows


def build_payload() -> dict[str, Any]:
    inputs = require_inputs()
    control_summary = as_dict(inputs["control_room"].get("summary"))
    gauntlet_summary = as_dict(inputs["gauntlet"].get("summary"))
    strongest = as_dict(inputs["gauntlet"].get("strongest_current"))
    first_summary = as_dict(inputs["first_buyer"].get("summary"))
    valuation_truth = as_dict(inputs["valuation"].get("current_truth"))
    valuation_state = as_dict(inputs["valuation"].get("valuation_state"))
    priceable = as_dict(valuation_state.get("current_priceable_offer"))
    sweep_stats = as_dict(
        inputs["valuation"].get("overall_locked_sweep_stats")
    )
    wiring_summary = as_dict(inputs["wiring"].get("summary"))
    targets = bounded_targets(inputs["first_buyer"])
    draft = as_dict(inputs["first_buyer"].get("primary_manual_email"))

    payload: dict[str, Any] = {
        "schema": "field_validation_outreach_board_v2",
        "generated_utc": now_utc(),
        "legacy_filename_notice": (
            "The filename is retained for downstream compatibility. This is a "
            "protocol-review opportunity board, not a field-validation outreach "
            "authorization."
        ),
        "purpose": (
            "Keep historical organization research and a bounded service offer "
            "available without converting source breadth or a failed candidate "
            "into performance, field, savings, or send-ready claims."
        ),
        "summary": {
            "internal_performance_champion_present": False,
            "measured_reference_candidate": strongest.get("family"),
            "development_selected_candidate": strongest.get(
                "development_selected_candidate"
            ),
            "reference_candidate_was_protocol_selected": bool(
                strongest.get("candidate_was_protocol_selected")
            ),
            "reference_holdout_wins": gauntlet_summary.get("holdout_wins"),
            "reference_holdout_count": gauntlet_summary.get("holdout_count"),
            "reference_mean_delta_vs_named_baseline": gauntlet_summary.get(
                "mean_delta_vs_named_baseline"
            ),
            "compatible_route_count": sweep_stats.get(
                "adapter_backed_route_count"
            ),
            "direct_measured_route_count": sweep_stats.get(
                "direct_measured_route_count"
            ),
            "conditioned_synthetic_route_count": sweep_stats.get(
                "source_conditioned_route_count"
            ),
            "baseline_comparison_count": sweep_stats.get(
                "baseline_comparison_count"
            ),
            "global_holm_positive_count": sweep_stats.get(
                "global_holm_positive_count"
            ),
            "performance_rows_reviewed": sweep_stats.get(
                "performance_rows_reviewed"
            ),
            "source_inventory_measured_count": wiring_summary.get(
                "live_source_measured_count"
            ),
            "source_inventory_measured_rows": wiring_summary.get(
                "total_measured_rows"
            ),
            "source_inventory_is_performance_evidence": False,
            "target_count": len(targets),
            "send_ready_target_count": 0,
            "recommended_first_buyer": first_summary.get(
                "recommended_first_buyer"
            ),
            "paid_protocol_review_scoping_allowed": bool(
                first_summary.get("paid_protocol_review_scoping_allowed")
            ),
            "manual_reviewed_outreach_allowed": False,
            "send_without_user_review_allowed": False,
            "bulk_email_allowed": False,
            "contact_scraping_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
        "proof_snapshot": {
            "current_champion": None,
            "measured_reference_candidate": valuation_truth.get(
                "reference_candidate"
            ),
            "development_selected_candidate": valuation_truth.get(
                "development_selected_candidate"
            ),
            "reference_candidate_was_protocol_selected": valuation_truth.get(
                "reference_candidate_was_protocol_selected"
            ),
            "named_baseline": valuation_truth.get("reference_named_baseline"),
            "holdout_wins": valuation_truth.get("reference_holdout_wins"),
            "holdout_count": valuation_truth.get("reference_holdout_count"),
            "mean_delta_vs_named_baseline": valuation_truth.get(
                "reference_mean_delta_vs_named_baseline"
            ),
            "claim_boundary": (
                "The geometry source inventory and conditioned-synthetic routes "
                "are research capacity. Kuramoto is direct measured negative "
                "evidence, not a current champion. Zero direct candidate cleared "
                "the complete all-baseline globally corrected promotion gate."
            ),
        },
        "commercial_offer": {
            "offer_type": "source-native benchmark and evidence protocol review",
            "paid_protocol_review_usd": priceable.get(
                "paid_protocol_review_usd", {}
            ),
            "benchmark_implementation_usd": priceable.get(
                "benchmark_implementation_usd", {}
            ),
            "platform_license": priceable.get("platform_license"),
            "enterprise_valuation_asserted": bool(
                valuation_state.get("enterprise_valuation_asserted")
            ),
            "proposal_blurb": inputs["valuation"].get("proposal_blurb", ""),
        },
        "ranked_targets": targets,
        "draft_template": {
            "recipient_selected": False,
            "subject": draft.get("subject"),
            "body": draft.get("body"),
            "status": "draft_only_not_ready_to_send",
            "why_not_ready": draft.get("why_not_autosend"),
        },
        "send_gate": {
            "send_allowed": False,
            "requires_current_official_source_verification": True,
            "requires_duplicate_send_reconciliation": True,
            "requires_exact_recipient": True,
            "requires_recipient_fit_review": True,
            "requires_exact_action_time_approval": True,
            "epri_inbound_only": True,
            "bulk_send_allowed": False,
        },
        "next_actions": [
            "Keep EPRI inbound-only.",
            "Do not treat any historical candidate organization as a current route.",
            "Verify one current official channel before selecting a recipient.",
            "Reconcile Sent mail and prior packets before drafting.",
            "Offer only the bounded protocol review or benchmark implementation.",
            "Require exact action-time approval before any external send.",
        ],
        "claim_controls": {
            "allowed": [
                "measured Kuramoto nonpromotion result",
                "source-task compatibility and baseline-registration capability",
                "bounded protocol-review and benchmark-implementation pricing",
            ],
            "blocked": [
                "current performance champion",
                "field-replay-ready candidate",
                "field validation",
                "realized savings",
                "fixed-dollar algorithm value",
                "live execution or trading edge",
                "current organization route without official re-verification",
            ],
        },
        "inputs": {
            "control_room": str(CONTROL_ROOM_JSON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "gauntlet": str(GAUNTLET_JSON.relative_to(ROOT)).replace("\\", "/"),
            "first_buyer": str(FIRST_BUYER_JSON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "valuation": str(VALUATION_JSON.relative_to(ROOT)).replace("\\", "/"),
            "wiring": str(WIRING_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    if control_summary.get("manual_outreach_ready"):
        raise ValueError("control room must keep manual outreach closed")
    payload["outreach_board_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "proof_snapshot": payload["proof_snapshot"],
            "commercial_offer": payload["commercial_offer"],
            "ranked_targets": payload["ranked_targets"],
            "send_gate": payload["send_gate"],
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    proof = payload["proof_snapshot"]
    offer = payload["commercial_offer"]
    lines = [
        "# Protocol Review Opportunity Board",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["legacy_filename_notice"],
        "",
        payload["purpose"],
        "",
        "## Current Truth",
        "",
        f"- Internal performance champion present: `{str(summary['internal_performance_champion_present']).lower()}`",
        f"- Current performance champion: `{proof['current_champion'] or 'none'}`",
        f"- Measured reference candidate: `{proof['measured_reference_candidate']}`",
        f"- Development-selected candidate: `{proof['development_selected_candidate']}`",
        f"- Reference candidate was protocol-selected: `{str(proof['reference_candidate_was_protocol_selected']).lower()}`",
        f"- Paired-day wins: `{proof['holdout_wins']}/{proof['holdout_count']}`",
        f"- Mean skill delta: `{proof['mean_delta_vs_named_baseline']}`",
        f"- Compatible routes: `{summary['compatible_route_count']}`",
        f"- Direct measured routes: `{summary['direct_measured_route_count']}`",
        f"- Conditioned-synthetic routes: `{summary['conditioned_synthetic_route_count']}`",
        f"- Baseline comparisons: `{summary['baseline_comparison_count']}`",
        f"- Global Holm promotions: `{summary['global_holm_positive_count']}`",
        f"- Source inventory: `{summary['source_inventory_measured_count']}` measured sources / `{summary['source_inventory_measured_rows']}` rows",
        f"- Source inventory is performance evidence: `{str(summary['source_inventory_is_performance_evidence']).lower()}`",
        "",
        proof["claim_boundary"],
        "",
        "## Priceable Offer",
        "",
        f"- Offer: `{offer['offer_type']}`",
        f"- Protocol review: `${offer['paid_protocol_review_usd'].get('low'):,}`-`${offer['paid_protocol_review_usd'].get('high'):,}`",
        f"- Benchmark implementation: `${offer['benchmark_implementation_usd'].get('low'):,}`-`${offer['benchmark_implementation_usd'].get('high'):,}`",
        f"- Enterprise valuation asserted: `{str(offer['enterprise_valuation_asserted']).lower()}`",
        "",
        offer["proposal_blurb"],
        "",
        "## Historical Research Candidates",
        "",
    ]
    for target in payload["ranked_targets"]:
        lines.extend(
            [
                f"### {target['rank']}. {target['organization']}",
                "",
                f"- Routing status: `{target['routing_status']}`",
                f"- Freshness: `{target['source_freshness_status']}`",
                f"- Send now allowed: `{str(target['send_now_allowed']).lower()}`",
                f"- Safe next action: {target['safe_next_action']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Send Gate",
            "",
            f"- Send allowed: `{str(payload['send_gate']['send_allowed']).lower()}`",
            f"- Bulk send allowed: `{str(payload['send_gate']['bulk_send_allowed']).lower()}`",
            f"- Exact action-time approval required: `{str(payload['send_gate']['requires_exact_action_time_approval']).lower()}`",
            f"- EPRI inbound-only: `{str(payload['send_gate']['epri_inbound_only']).lower()}`",
            "",
            "## Bounded Draft Template",
            "",
            f"- Recipient selected: `{str(payload['draft_template']['recipient_selected']).lower()}`",
            f"- Status: `{payload['draft_template']['status']}`",
            f"- Subject: {payload['draft_template']['subject']}",
            "",
            "## Next Actions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["next_actions"])
    lines.extend(
        [
            "",
            f"Outreach board SHA-256: `{payload['outreach_board_sha256']}`",
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
                "targets": payload["summary"]["target_count"],
                "send_ready_targets": payload["summary"][
                    "send_ready_target_count"
                ],
                "send_allowed": payload["send_gate"]["send_allowed"],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
