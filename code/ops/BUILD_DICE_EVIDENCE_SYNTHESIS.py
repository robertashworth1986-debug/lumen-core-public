from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
GRANTS = ROOT / "grant_submissions"
DICE_DIR = GRANTS / "DICE_HR001126S0010"

PRELIM_DIR = ROOT / "out" / "dice_preliminary" / "20260613T_DICE_V1_500A_200PAIRS_OPT"
CONTRACT_DIR = ROOT / "out" / "dice_constraint_contract" / "20260618T_DICE_CONTRACT_V2_ROLE_SHUFFLE"
LIVE_REPLAY = OUT / "dice_live_breadth_replay_latest.json"
LIVE_BREADTH_ANNEX = OUT / "grant_live_breadth_provenance_annex_latest.json"

OUT_JSON = OUT / "dice_evidence_synthesis_latest.json"
OUT_MD = DICE_DIR / "DICE_EVIDENCE_SYNTHESIS_2026-06-20.md"

SENSITIVE_PATTERNS = [
    re.compile(r"\bUEI\s+[A-Z0-9]{8,16}\b", re.IGNORECASE),
    re.compile(r"\bCAGE/NCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
    re.compile(r"\bCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
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


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def sanitize_text(text: str) -> str:
    clean = text
    for pattern in SENSITIVE_PATTERNS:
        clean = pattern.sub("[REDACTED]", clean)
    return clean


def ci_text(values: list[Any] | tuple[Any, ...] | None) -> str:
    if not values or len(values) != 2:
        return "n/a"
    return f"[{float(values[0]):.4f}, {float(values[1]):.4f}]"


def pct(value: Any) -> str:
    try:
        return f"{float(value):.3f}%"
    except Exception:
        return "n/a"


def points(value: Any) -> str:
    try:
        return f"{float(value):.3f} points"
    except Exception:
        return "n/a"


def extract_preliminary(summary: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    paired = summary.get("paired_statistics", {}) if isinstance(summary, dict) else {}
    config = summary.get("configuration", {}) if isinstance(summary, dict) else {}

    def metric(name: str, unit: str) -> dict[str, Any]:
        row = paired.get(name, {}) if isinstance(paired, dict) else {}
        return {
            "metric": name,
            "mean": row.get("mean"),
            "median": row.get("median"),
            "bootstrap_95_ci": row.get("bootstrap_95_ci", []),
            "unit": unit,
        }

    return {
        "lane": "preliminary_peer_mesh",
        "schema": summary.get("schema"),
        "generated_utc": summary.get("generated_utc"),
        "summary_path": rel(PRELIM_DIR / "summary.json"),
        "scorecard_path": rel(PRELIM_DIR / "SCORECARD.md"),
        "manifest_path": rel(PRELIM_DIR / "manifest.sha256.json"),
        "manifest_file_count": len(manifest.get("files", {}) or {}),
        "evidence_boundary": summary.get("evidence_boundary"),
        "configuration": config,
        "metrics": [
            metric("mission_success_rate_points", "percentage_points"),
            metric("message_reduction_pct", "percent_reduction"),
            metric("recovery_message_reduction_pct", "percent_reduction"),
            metric("role_coherence_rate_points", "percentage_points"),
        ],
        "grant_use": (
            "Supports a Phase I measurement hypothesis that localized peer routing "
            "can reduce coordination/recovery message overhead in synthetic task "
            "allocation while preserving high completion."
        ),
        "not_claimed": [
            "DICE program metric attainment",
            "foundation-model or language-agent performance",
            "DoD operational performance",
            "adversarial security",
        ],
    }


def extract_contract(summary: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    validation = summary.get("validation", {}) if isinstance(summary, dict) else {}
    conditions = validation.get("conditions", {}) if isinstance(validation, dict) else {}
    condition_rows: list[dict[str, Any]] = []
    for name, payload in conditions.items():
        metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
        peer = metrics.get("peer_reputation", {}) if isinstance(metrics, dict) else {}
        contract = metrics.get("constraint_contract", {}) if isinstance(metrics, dict) else {}
        paired = metrics.get("paired", {}) if isinstance(metrics, dict) else {}

        def paired_metric(metric_name: str) -> dict[str, Any]:
            row = paired.get(metric_name, {}) if isinstance(paired, dict) else {}
            return {
                "mean_delta": row.get("mean_delta"),
                "bootstrap_95pct_interval": row.get("bootstrap_95pct_interval", []),
                "favorable_scenario_fraction": row.get("favorable_scenario_fraction"),
                "scenario_count": row.get("scenario_count"),
            }

        condition_rows.append(
            {
                "condition": str(name),
                "peer_safe_completion_rate": peer.get("safe_completion_rate"),
                "contract_safe_completion_rate": contract.get("safe_completion_rate"),
                "contract_false_rejection_rate": contract.get("false_rejection_rate"),
                "safe_completion_rate_delta": paired_metric("safe_completion_rate"),
                "constraint_violation_rate_delta": paired_metric("constraint_violation_rate"),
                "messages_per_safe_completion_delta": paired_metric("messages_per_safe_completion"),
                "compromised_assignment_rate_delta": paired_metric("compromised_assignment_rate"),
            }
        )

    safe_positive = all(
        float(row["safe_completion_rate_delta"].get("mean_delta") or 0.0) > 0.0
        for row in condition_rows
    )
    violation_negative = all(
        float(row["constraint_violation_rate_delta"].get("mean_delta") or 0.0) < 0.0
        for row in condition_rows
    )
    message_negative = all(
        float(row["messages_per_safe_completion_delta"].get("mean_delta") or 0.0) < 0.0
        for row in condition_rows
    )
    high_false_rejection_conditions = [
        row["condition"]
        for row in condition_rows
        if float(row.get("contract_false_rejection_rate") or 0.0) >= 0.10
    ]
    compromised_worse_conditions = [
        row["condition"]
        for row in condition_rows
        if float(row["compromised_assignment_rate_delta"].get("mean_delta") or 0.0) > 0.0
    ]

    return {
        "lane": "constraint_contract",
        "schema": summary.get("schema"),
        "generated_utc": summary.get("generated_utc"),
        "summary_path": rel(CONTRACT_DIR / "summary.json"),
        "scorecard_path": rel(CONTRACT_DIR / "SCORECARD.md"),
        "manifest_path": rel(CONTRACT_DIR / "manifest.sha256.json"),
        "manifest_file_count": len(manifest.get("files", {}) or {}),
        "evidence_boundary": summary.get("evidence_boundary"),
        "development_selected_margin": (summary.get("development", {}) or {}).get("selected_margin"),
        "validation_condition_count": len(condition_rows),
        "validation_scenarios_per_condition": validation.get("scenarios_per_condition"),
        "condition_rows": condition_rows,
        "robust_observations": {
            "safe_completion_delta_positive_all_conditions": safe_positive,
            "constraint_violation_delta_negative_all_conditions": violation_negative,
            "messages_per_safe_completion_delta_negative_all_conditions": message_negative,
        },
        "known_failure_modes": {
            "false_rejection_ge_10pct_conditions": high_false_rejection_conditions,
            "compromised_assignment_worse_conditions": compromised_worse_conditions,
            "collusive_forgery_boundary": "Locally consistent forged contracts can pass deterministic checks in this generated model.",
        },
        "grant_use": (
            "Supports a concrete Phase I research task for contract-field checks, "
            "role evidence, stale-evidence handling, and adversarial stress testing."
        ),
        "not_claimed": [
            "semantic correctness",
            "cryptographic computation cost",
            "language-agent performance",
            "operational defense performance",
            "adversarial security",
        ],
    }


def extract_live_replay(summary: dict[str, Any]) -> dict[str, Any]:
    paired = summary.get("paired_metrics", {}) if isinstance(summary, dict) else {}
    configuration = summary.get("configuration", {}) if isinstance(summary, dict) else {}
    source_manifest = summary.get("source_manifest", {}) if isinstance(summary, dict) else {}
    claim_gate = summary.get("claim_gate", {}) if isinstance(summary, dict) else {}

    def metric(name: str, unit: str) -> dict[str, Any]:
        row = paired.get(name, {}) if isinstance(paired, dict) else {}
        return {
            "metric": name,
            "mean_delta": row.get("mean_delta"),
            "min_delta": row.get("min_delta"),
            "max_delta": row.get("max_delta"),
            "favorable_scenario_fraction": row.get("favorable_scenario_fraction"),
            "scenario_count": row.get("scenario_count"),
            "unit": unit,
        }

    return {
        "lane": "live_breadth_replay",
        "schema": summary.get("schema"),
        "generated_utc": summary.get("generated_utc"),
        "summary_path": rel(LIVE_REPLAY),
        "scorecard_path": rel(DICE_DIR / "DICE_LIVE_BREADTH_REPLAY_2026-06-20.md"),
        "evidence_mode": summary.get(
            "evidence_mode",
            "primary_live_pulled_source_rows_with_deterministic_replay_labels",
        ),
        "primary_evidence_source": summary.get("primary_evidence_source", "frozen_live_pulled_rows"),
        "synthetic_role": summary.get(
            "synthetic_role",
            "secondary_control_labels_ablation_and_failure_injection_only",
        ),
        "evidence_boundary": summary.get(
            "evidence_boundary",
            "Live-breadth replay artifact has not been generated yet.",
        ),
        "source_count": source_manifest.get("source_count", 0),
        "source_types": sorted(
            {
                str(source.get("source_type"))
                for source in source_manifest.get("sources", []) or []
                if isinstance(source, dict) and source.get("source_type")
            }
        ),
        "configuration": configuration,
        "metrics": [
            metric("safe_completion_rate", "rate_delta"),
            metric("constraint_violation_rate", "rate_delta"),
            metric("messages_per_safe_completion", "message_delta"),
            metric("false_rejection_rate", "rate_delta"),
        ],
        "grant_use": (
            "Promotes a hashable replay lane using live-pulled operational and market "
            "time-series as the realism layer, with synthetic controls retained only for labels and ablations."
        ),
        "known_boundary": (
            "Source data do not carry native DICE task labels; replay labels are "
            "deterministic derived labels and cannot prove DICE metric attainment."
        ),
        "claim_gate": {
            "ready_for_portal_upload": bool(claim_gate.get("ready_for_portal_upload", False)),
            "ready_for_submit": bool(claim_gate.get("ready_for_submit", False)),
            "live_replay_proves_dice_metric_attainment": bool(
                claim_gate.get("live_replay_proves_dice_metric_attainment", False)
            ),
            "live_replay_proves_operational_performance": bool(
                claim_gate.get("live_replay_proves_operational_performance", False)
            ),
            "live_replay_proves_trading_profit": bool(
                claim_gate.get("live_replay_proves_trading_profit", False)
            ),
            "synthetic_primary_evidence": bool(claim_gate.get("synthetic_primary_evidence", False)),
        },
        "not_claimed": [
            "DICE program metric attainment",
            "field validation",
            "DoD operational performance",
            "trading profit or grant merit",
            "adversarial security",
        ],
    }


def extract_live_breadth_annex(summary: dict[str, Any]) -> dict[str, Any]:
    live = summary.get("live_breadth_state", {}) if isinstance(summary, dict) else {}
    truth = summary.get("truth_chain_state", {}) if isinstance(summary, dict) else {}
    claim_gate = summary.get("claim_gate", {}) if isinstance(summary, dict) else {}
    reviewer_use = summary.get("reviewer_use", {}) if isinstance(summary, dict) else {}

    return {
        "lane": "live_breadth_provenance_annex",
        "schema": summary.get("schema", ""),
        "generated_utc": summary.get("generated_utc", ""),
        "summary_path": rel(LIVE_BREADTH_ANNEX),
        "scorecard_path": rel(GRANTS / "LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md"),
        "primary_evidence_mode": live.get("primary_evidence_mode", ""),
        "enabled_sources": live.get("enabled_sources", 0),
        "measured_sources": live.get("measured_sources", 0),
        "measured_coverage_pct": live.get("measured_coverage_pct", 0.0),
        "live_measured_hourly_value_usd": live.get("live_measured_hourly_value_usd", 0.0),
        "live_measured_annual_value_usd": live.get("live_measured_annual_value_usd", 0.0),
        "context_only_hourly_value_usd": live.get("context_only_hourly_value_usd", 0.0),
        "context_only_annual_value_usd": live.get("context_only_annual_value_usd", 0.0),
        "truth_chain_entry_sha256": truth.get("entry_sha256", ""),
        "truth_chain_promoted_annual_value_usd": truth.get("promoted_live_measured_annual_value_usd", 0.0),
        "grant_use": reviewer_use.get(
            "grant_language",
            "Use only as a provenance and live-measurement discipline artifact.",
        ),
        "known_boundary": reviewer_use.get(
            "live_breadth_role",
            "Live breadth is not native ground truth for DICE or field performance.",
        ),
        "claim_gate": {
            "ready_for_portal_upload": bool(claim_gate.get("ready_for_portal_upload", False)),
            "ready_for_submit": bool(claim_gate.get("ready_for_submit", False)),
            "grant_merit_proven": bool(claim_gate.get("grant_merit_proven", False)),
            "field_performance_proven": bool(claim_gate.get("field_performance_proven", False)),
            "trading_profit_proven": bool(claim_gate.get("trading_profit_proven", False)),
            "context_only_promoted_as_live_proof": bool(
                claim_gate.get("context_only_promoted_as_live_proof", False)
            ),
        },
        "not_claimed": [
            "DICE program metric attainment",
            "grant merit or award probability",
            "field validation",
            "trading profit",
            "customer savings",
        ],
    }


def build_synthesis() -> dict[str, Any]:
    prelim_summary = read_json(PRELIM_DIR / "summary.json")
    prelim_manifest = read_json(PRELIM_DIR / "manifest.sha256.json")
    contract_summary = read_json(CONTRACT_DIR / "summary.json")
    contract_manifest = read_json(CONTRACT_DIR / "manifest.sha256.json")
    live_summary = read_json(LIVE_REPLAY)
    annex_summary = read_json(LIVE_BREADTH_ANNEX)

    preliminary = extract_preliminary(prelim_summary, prelim_manifest)
    contract = extract_contract(contract_summary, contract_manifest)
    live_replay = extract_live_replay(live_summary)
    live_annex = extract_live_breadth_annex(annex_summary)

    payload = {
        "schema": "dice_evidence_synthesis_v1",
        "generated_utc": now_utc(),
        "reviewer_positioning": (
            "Use this as measurable preliminary evidence and a Phase I validation "
            "plan, not as a claim that DICE performance has been proven."
        ),
        "source_runs": [preliminary, contract, live_replay, live_annex],
        "what_this_supports": [
            "A live-breadth replay lane maps frozen Kraken and EIA time-series windows into deterministic stress scenarios while keeping replay-label limits explicit.",
            "A provenance-gated live-breadth annex separates promoted live-measured signals from context-only estimates and anchors the promoted value in the truth chain.",
            "A reproducible synthetic benchmark harness exists and is hash-manifested.",
            "Peer/local control reduced message and recovery-message overhead in the preliminary synthetic benchmark.",
            "Constraint-contract checks improved safe completion and reduced modeled constraint violations across five generated validation conditions.",
            "The evidence is strong enough to justify a Phase I work plan with stronger agents, independent datasets, and adversarial evaluation.",
        ],
        "what_this_does_not_support": [
            "Do not claim DICE performance has been proven.",
            "Do not claim operational DoD deployment performance.",
            "Do not claim foundation-model or TA3-scale agent validation.",
            "Do not claim adversarial security or cryptographic cost measurement.",
            "Do not claim trading, live-breadth, or frozen-delta results prove DICE merit.",
            "Do not claim the live-measured economic signal is customer savings, revenue, valuation proof, or grant merit.",
            "Do not claim live-breadth replay proves field performance; it is a frozen stress replay lane.",
        ],
        "phase_i_validation_upgrades": [
            "Replace stochastic task executors with instrumented heterogeneous LLM/tool agents or a TA3-compatible adaptor.",
            "Measure byte cost, latency, cryptographic overhead, and failure recovery cost instead of only counting logical messages.",
            "Add preregistered attack sets for role poisoning, collusion, stale evidence, monitor drift, and locally consistent forged contracts.",
            "Run ablations against centralized, peer-reputation, contract-field, and hybrid variants under identical seeds.",
            "Expand the live-replay adapter beyond Kraken/EIA into additional live-breadth sectors only after each source has a frozen manifest and replay-label contract.",
            "Create independent evaluator packets with frozen seeds, manifests, scorecards, and refusal-to-overclaim gates.",
        ],
        "claim_gate": {
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
            "human_action_time_approval_required": True,
            "boundary": (
                "This artifact improves reviewer clarity only. It does not authorize "
                "upload, signature, certification, submission, award-likelihood claims, "
                "or legal/compliance representations."
            ),
        },
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    prelim = next(row for row in payload["source_runs"] if row["lane"] == "preliminary_peer_mesh")
    contract = next(row for row in payload["source_runs"] if row["lane"] == "constraint_contract")
    live = next(row for row in payload["source_runs"] if row["lane"] == "live_breadth_replay")
    annex = next(row for row in payload["source_runs"] if row["lane"] == "live_breadth_provenance_annex")
    prelim_metrics = {row["metric"]: row for row in prelim["metrics"]}
    live_metrics = {row["metric"]: row for row in live["metrics"]}

    lines = [
        "# DICE Evidence Synthesis",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Reviewer Positioning",
        "",
        payload["reviewer_positioning"],
        "",
        "## What This Supports",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["what_this_supports"])
    lines.extend(["", "## What This Does Not Support", ""])
    lines.extend(f"- {item}" for item in payload["what_this_does_not_support"])
    lines.extend(
        [
            "",
            "## Preliminary Peer-Mesh Benchmark",
            "",
            f"- Evidence boundary: {prelim['evidence_boundary']}",
            f"- Configuration: {prelim['configuration']}",
            f"- Summary: {prelim['summary_path']}",
            f"- Manifest: {prelim['manifest_path']}",
            "",
            "| Metric | Mean | 95% bootstrap interval | Reviewer use |",
            "|---|---:|---:|---|",
            (
                "| Mission success delta | "
                f"{points(prelim_metrics['mission_success_rate_points']['mean'])} | "
                f"{ci_text(prelim_metrics['mission_success_rate_points']['bootstrap_95_ci'])} | "
                "Completion preserved in the synthetic setting. |"
            ),
            (
                "| Message reduction | "
                f"{pct(prelim_metrics['message_reduction_pct']['mean'])} | "
                f"{ci_text(prelim_metrics['message_reduction_pct']['bootstrap_95_ci'])} | "
                "Evidence for measurable coordination-cost reduction. |"
            ),
            (
                "| Recovery-message reduction | "
                f"{pct(prelim_metrics['recovery_message_reduction_pct']['mean'])} | "
                f"{ci_text(prelim_metrics['recovery_message_reduction_pct']['bootstrap_95_ci'])} | "
                "Evidence for lower modeled recovery overhead. |"
            ),
            (
                "| Role-coherence delta | "
                f"{points(prelim_metrics['role_coherence_rate_points']['mean'])} | "
                f"{ci_text(prelim_metrics['role_coherence_rate_points']['bootstrap_95_ci'])} | "
                "Evidence for a role-consistency measurement lane. |"
            ),
            "",
            "## Constraint-Contract Stress Benchmark",
            "",
            f"- Evidence boundary: {contract['evidence_boundary']}",
            f"- Validation conditions: {contract['validation_condition_count']}",
            f"- Scenarios per condition: {contract['validation_scenarios_per_condition']}",
            f"- Selected development margin: {contract['development_selected_margin']}",
            f"- Summary: {contract['summary_path']}",
            f"- Manifest: {contract['manifest_path']}",
            "",
            "| Condition | Safe-completion delta | Violation-rate delta | Message delta | False rejection |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in contract["condition_rows"]:
        safe = row["safe_completion_rate_delta"]
        violation = row["constraint_violation_rate_delta"]
        message = row["messages_per_safe_completion_delta"]
        lines.append(
            f"| {row['condition']} | "
            f"{float(safe.get('mean_delta') or 0.0):.4f} "
            f"{ci_text(safe.get('bootstrap_95pct_interval'))} | "
            f"{float(violation.get('mean_delta') or 0.0):.4f} "
            f"{ci_text(violation.get('bootstrap_95pct_interval'))} | "
            f"{float(message.get('mean_delta') or 0.0):.4f} "
            f"{ci_text(message.get('bootstrap_95pct_interval'))} | "
            f"{float(row.get('contract_false_rejection_rate') or 0.0):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Live-Breadth Replay Lane",
            "",
            f"- Evidence mode: {live['evidence_mode']}",
            f"- Primary evidence source: {live['primary_evidence_source']}",
            f"- Synthetic role: {live['synthetic_role']}",
            f"- Evidence boundary: {live['evidence_boundary']}",
            f"- Source count: {live['source_count']}",
            f"- Source types: {', '.join(live['source_types']) if live['source_types'] else 'n/a'}",
            f"- Configuration: {live['configuration']}",
            f"- Summary: {live['summary_path']}",
            f"- Scorecard: {live['scorecard_path']}",
            f"- Boundary to own: {live['known_boundary']}",
            "",
            "Claim gate:",
            "",
            f"- ready_for_portal_upload: {str(live['claim_gate']['ready_for_portal_upload']).lower()}",
            f"- ready_for_submit: {str(live['claim_gate']['ready_for_submit']).lower()}",
            f"- live_replay_proves_dice_metric_attainment: {str(live['claim_gate']['live_replay_proves_dice_metric_attainment']).lower()}",
            f"- live_replay_proves_trading_profit: {str(live['claim_gate']['live_replay_proves_trading_profit']).lower()}",
            f"- synthetic_primary_evidence: {str(live['claim_gate']['synthetic_primary_evidence']).lower()}",
            "",
            "| Metric | Mean delta | Favorable fraction | Scenario count | Reviewer use |",
            "|---|---:|---:|---:|---|",
            (
                "| Safe completion | "
                f"{float(live_metrics['safe_completion_rate'].get('mean_delta') or 0.0):+.4f} | "
                f"{float(live_metrics['safe_completion_rate'].get('favorable_scenario_fraction') or 0.0):.3f} | "
                f"{int(live_metrics['safe_completion_rate'].get('scenario_count') or 0)} | "
                "Stress-replay signal, not DICE metric proof. |"
            ),
            (
                "| Constraint violation | "
                f"{float(live_metrics['constraint_violation_rate'].get('mean_delta') or 0.0):+.4f} | "
                f"{float(live_metrics['constraint_violation_rate'].get('favorable_scenario_fraction') or 0.0):.3f} | "
                f"{int(live_metrics['constraint_violation_rate'].get('scenario_count') or 0)} | "
                "Supports a constraint-check validation lane. |"
            ),
            (
                "| Messages per safe completion | "
                f"{float(live_metrics['messages_per_safe_completion'].get('mean_delta') or 0.0):+.4f} | "
                f"{float(live_metrics['messages_per_safe_completion'].get('favorable_scenario_fraction') or 0.0):.3f} | "
                f"{int(live_metrics['messages_per_safe_completion'].get('scenario_count') or 0)} | "
                "Shows modeled coordination-cost behavior on frozen live windows. |"
            ),
            (
                "| False rejection | "
                f"{float(live_metrics['false_rejection_rate'].get('mean_delta') or 0.0):+.4f} | "
                f"{float(live_metrics['false_rejection_rate'].get('favorable_scenario_fraction') or 0.0):.3f} | "
                f"{int(live_metrics['false_rejection_rate'].get('scenario_count') or 0)} | "
                "Known cost to reduce in Phase I. |"
            ),
            "",
        ]
    )

    lines.extend(
        [
            "## Provenance-Gated Live-Breadth Annex",
            "",
            f"- Primary evidence mode: `{annex['primary_evidence_mode'] or 'unknown'}`",
            f"- Measured sources: {annex['measured_sources']}/{annex['enabled_sources']} ({float(annex['measured_coverage_pct'] or 0.0):.2f}%)",
            f"- Promoted live-measured hourly value signal: ${float(annex['live_measured_hourly_value_usd'] or 0.0):,.2f}",
            f"- Promoted live-measured annual value signal: ${float(annex['live_measured_annual_value_usd'] or 0.0):,.2f}",
            f"- Context-only hourly surface: ${float(annex['context_only_hourly_value_usd'] or 0.0):,.2f}",
            f"- Context-only annual surface: ${float(annex['context_only_annual_value_usd'] or 0.0):,.2f}",
            f"- Truth-chain entry SHA-256: `{annex['truth_chain_entry_sha256']}`",
            f"- Annex: {annex['scorecard_path']}",
            f"- Grant use: {annex['grant_use']}",
            f"- Boundary to own: {annex['known_boundary']}",
            "",
            "Claim gate:",
            "",
            f"- ready_for_portal_upload: {str(annex['claim_gate']['ready_for_portal_upload']).lower()}",
            f"- ready_for_submit: {str(annex['claim_gate']['ready_for_submit']).lower()}",
            f"- grant_merit_proven: {str(annex['claim_gate']['grant_merit_proven']).lower()}",
            f"- field_performance_proven: {str(annex['claim_gate']['field_performance_proven']).lower()}",
            f"- trading_profit_proven: {str(annex['claim_gate']['trading_profit_proven']).lower()}",
            f"- context_only_promoted_as_live_proof: {str(annex['claim_gate']['context_only_promoted_as_live_proof']).lower()}",
            "",
        ]
    )

    failure_modes = contract["known_failure_modes"]
    lines.extend(
        [
            "",
            "## Failure Modes To Own",
            "",
            (
                "- False rejection exceeds 10% in: "
                + ", ".join(failure_modes["false_rejection_ge_10pct_conditions"])
            ),
            (
                "- Compromised-assignment rate worsens in: "
                + ", ".join(failure_modes["compromised_assignment_worse_conditions"])
            ),
            f"- {failure_modes['collusive_forgery_boundary']}",
            "",
            "## Phase I Validation Upgrades",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["phase_i_validation_upgrades"])
    lines.extend(
        [
            "",
            "## Claim Gate",
            "",
            "- ready_for_portal_upload: false",
            "- ready_for_submit: false",
            "- human_action_time_approval_required: true",
            f"- boundary: {payload['claim_gate']['boundary']}",
            "",
        ]
    )
    return sanitize_text("\n".join(lines))


def write_synthesis(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_synthesis()
    OUT.mkdir(parents=True, exist_ok=True)
    DICE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    payload = write_synthesis()
    print(json.dumps({"wrote_json": rel(OUT_JSON), "wrote_md": rel(OUT_MD), "schema": payload["schema"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
