from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LEXICON = ROOT / "config" / "quant_hub_lexicon_v1.json"
OUT_JSON = ROOT / "out" / "ops" / "quant_hub_reviewer_context_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "quant_hub_reviewer_context.json"
OUT_MD = ROOT / "docs" / "QUANT_HUB_REVIEWER_CONTEXT_2026-07-13.md"

SOURCE_PATHS = {
    "prior_proof_vault": ROOT / "out" / "ops" / "external_proof_vault_manifest_latest.json",
    "estate_index": ROOT / "out" / "ops" / "lumencore_estate_master_index_latest.json",
    "live_source_measurement": ROOT / "out" / "ops" / "live_source_measurement_maximizer_latest.json",
    "locked_replay": ROOT / "out" / "ops" / "locked_source_baseline_replay_sweep_latest.json",
    "reviewer_gate": ROOT / "out" / "ops" / "funding_sprint_reviewer_gate_latest.json",
    "faa_sdr_10k": ROOT / "out" / "ops" / "faa_sdr_10k_benchmark_latest.json",
    "eia_prospective_router": ROOT
    / "out"
    / "eia_grid_prospective_hybrid_router"
    / "prospective_status_latest.json",
    "mda_feasibility_v1": ROOT
    / "out"
    / "mda_control_mapping_feasibility"
    / "mda_control_mapping_feasibility_latest.json",
    "mda_open_set_v2": ROOT
    / "out"
    / "mda_control_mapping_open_set_v2"
    / "mda_control_mapping_open_set_latest.json",
}

PRIVATE_MARKERS = (
    "private_estate",
    "patent_19_281_546",
    "cp575notice",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_required(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"required reviewer-context input is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"required reviewer-context input is not an object: {path}")
    return payload


def require_dict(payload: dict[str, Any], key: str, source: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{source}.{key} must be an object")
    return value


def require_value(payload: dict[str, Any], key: str, source: str) -> Any:
    if key not in payload:
        raise ValueError(f"{source}.{key} is required")
    return payload[key]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def assert_public_safe(payload: Any, location: str = "root") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert_public_safe(value, f"{location}.{key}")
        return
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            assert_public_safe(value, f"{location}[{index}]")
        return
    if isinstance(payload, str):
        normalized = payload.casefold().replace("\\", "/")
        for marker in PRIVATE_MARKERS:
            if marker in normalized:
                raise ValueError(f"private marker {marker!r} found at {location}")


def source_receipts(paths: dict[str, Path]) -> tuple[list[dict[str, Any]], str]:
    receipts = []
    for source_id, path in sorted(paths.items()):
        if not path.is_file():
            raise FileNotFoundError(f"required reviewer-context source is missing: {path}")
        receipts.append(
            {
                "source_id": source_id,
                "path": repo_path(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return receipts, canonical_sha256(receipts)


def build_context() -> dict[str, Any]:
    lexicon = read_json_required(LEXICON)
    sources = {name: read_json_required(path) for name, path in SOURCE_PATHS.items()}
    receipts, input_chain_sha256 = source_receipts({"lexicon": LEXICON, **SOURCE_PATHS})

    identity = require_dict(lexicon, "identity", "lexicon")
    maturity_policy = require_dict(lexicon, "level_policy", "lexicon")
    human_policy = require_dict(lexicon, "human_authority_policy", "lexicon")

    vault = sources["prior_proof_vault"]
    vault_summary = require_dict(vault, "summary", "prior_proof_vault")
    vault_copy = require_dict(vault, "copy_result", "prior_proof_vault")

    estate_summary = require_dict(sources["estate_index"], "summary", "estate_index")
    live_summary = require_dict(sources["live_source_measurement"], "summary", "live_source_measurement")
    replay = sources["locked_replay"]
    replay_summary = require_dict(replay, "summary", "locked_replay")
    replay_gates = require_dict(replay, "claim_gates", "locked_replay")
    reviewer = sources["reviewer_gate"]
    reviewer_summary = require_dict(reviewer, "summary", "reviewer_gate")
    faa = sources["faa_sdr_10k"]
    faa_execution = require_dict(faa, "execution", "faa_sdr_10k")
    faa_splits = require_dict(faa, "splits", "faa_sdr_10k")
    faa_gate = require_dict(faa, "promotion_gate", "faa_sdr_10k")
    faa_rolls = require_dict(faa, "rolls_royce_exploratory", "faa_sdr_10k")
    faa_leaderboard = require_value(faa, "holdout_leaderboard", "faa_sdr_10k")
    if not isinstance(faa_leaderboard, list):
        raise ValueError("faa_sdr_10k.holdout_leaderboard must be an array")
    faa_candidate = next((row for row in faa_leaderboard if row.get("candidate")), None)
    faa_baseline_name = str(require_value(faa, "strongest_approved_baseline", "faa_sdr_10k"))
    faa_baseline = next((row for row in faa_leaderboard if row.get("model") == faa_baseline_name), None)
    if not isinstance(faa_candidate, dict) or not isinstance(faa_baseline, dict):
        raise ValueError("faa_sdr_10k leaderboard must identify the candidate and strongest baseline")
    eia = sources["eia_prospective_router"]
    eia_gates = require_dict(eia, "sample_gates", "eia_prospective_router")

    mda_v1 = sources["mda_feasibility_v1"]
    mda_v1_counts = require_dict(mda_v1, "fixture_counts", "mda_feasibility_v1")
    mda_v1_metrics = require_dict(mda_v1, "holdout_metrics", "mda_feasibility_v1")
    mda_v1_candidate = require_dict(
        mda_v1_metrics,
        "hybrid_static_then_lexical_v1",
        "mda_feasibility_v1.holdout_metrics",
    )
    mda_v1_gate = require_dict(mda_v1, "gate", "mda_feasibility_v1")

    mda_v2 = sources["mda_open_set_v2"]
    mda_v2_counts = require_dict(mda_v2, "fixture_counts", "mda_open_set_v2")
    mda_v2_metrics = require_dict(mda_v2, "holdout_metrics", "mda_open_set_v2")
    mda_v2_candidate = require_dict(
        mda_v2_metrics,
        "hybrid_static_then_open_set_lexical_v2",
        "mda_open_set_v2.holdout_metrics",
    )
    mda_v2_gate = require_dict(mda_v2, "gate", "mda_open_set_v2")

    prior_vault_verified = bool(vault_copy.get("all_copied_hashes_verified")) and (
        int(vault_copy.get("verified_count", -1)) == int(vault_summary.get("ready_count", -2))
    )

    proof_cards = [
        {
            "proof_id": "prooflock_prior_vault",
            "title": "Prior external proof-vault custody",
            "evidence_class": "provenance_and_custody",
            "attained_maturity_level": 3,
            "status": "verified" if prior_vault_verified else "not_verified",
            "facts": {
                "artifact_count": require_value(vault_summary, "artifact_count", "prior_proof_vault.summary"),
                "ready_count": require_value(vault_summary, "ready_count", "prior_proof_vault.summary"),
                "verified_count": require_value(vault_copy, "verified_count", "prior_proof_vault.copy_result"),
                "all_copied_hashes_verified": prior_vault_verified,
                "packet_name": Path(str(require_value(vault, "packet_dir", "prior_proof_vault"))).name,
                "manifest_source_sha256": sha256_file(SOURCE_PATHS["prior_proof_vault"]),
            },
            "claim_boundary": require_value(vault, "claim_boundary", "prior_proof_vault"),
        },
        {
            "proof_id": "estate_inventory",
            "title": "Public-safe estate inventory",
            "evidence_class": "asset_inventory",
            "attained_maturity_level": 1,
            "status": "indexed",
            "facts": {
                "managed_file_count": require_value(estate_summary, "managed_file_count", "estate_index.summary"),
                "managed_total_bytes": require_value(estate_summary, "managed_total_bytes", "estate_index.summary"),
                "inventory_chain_sha256": require_value(estate_summary, "inventory_chain_sha256", "estate_index.summary"),
                "secret_content_indexed": require_value(estate_summary, "secret_content_indexed", "estate_index.summary"),
                "sensitive_paths_redacted": require_value(
                    estate_summary,
                    "sensitive_paths_redacted_from_public_payload",
                    "estate_index.summary",
                ),
            },
            "claim_boundary": "An inventory proves discoverability and custody metadata, not scientific validity, ownership, novelty, or commercial value.",
        },
        {
            "proof_id": "live_source_measurement",
            "title": "Measured source breadth",
            "evidence_class": "fresh_source_measurement",
            "attained_maturity_level": 3,
            "status": "measured_with_thin_sources",
            "facts": {
                "enabled_sources": require_value(live_summary, "enabled_sources", "live_source_measurement.summary"),
                "measured_sources": require_value(live_summary, "measured_sources", "live_source_measurement.summary"),
                "failed_or_thin_sources": require_value(
                    live_summary,
                    "failed_or_thin_sources",
                    "live_source_measurement.summary",
                ),
                "total_measured_rows": require_value(
                    live_summary,
                    "total_measured_rows",
                    "live_source_measurement.summary",
                ),
                "coverage_pct": require_value(live_summary, "coverage_pct", "live_source_measurement.summary"),
            },
            "claim_boundary": require_value(live_summary, "claim_boundary", "live_source_measurement.summary"),
        },
        {
            "proof_id": "locked_source_baseline_replay",
            "title": "Locked source-conditioned baseline replay",
            "evidence_class": "source_conditioned_replay",
            "attained_maturity_level": 3,
            "status": "complete_with_wins_and_non_wins",
            "facts": {
                "adapter_backed_routes": require_value(replay_summary, "adapter_backed_routes", "locked_replay.summary"),
                "baseline_comparison_count": require_value(
                    replay_summary,
                    "baseline_comparison_count",
                    "locked_replay.summary",
                ),
                "candidate_win_count": require_value(replay_summary, "candidate_win_count", "locked_replay.summary"),
                "candidate_loss_or_tie_count": require_value(
                    replay_summary,
                    "candidate_loss_or_tie_count",
                    "locked_replay.summary",
                ),
                "estimated_rows_replayed": require_value(
                    replay_summary,
                    "estimated_rows_replayed",
                    "locked_replay.summary",
                ),
                "numeric_samples_read": require_value(
                    replay_summary,
                    "numeric_samples_read",
                    "locked_replay.summary",
                ),
                "energy_proxy_routes_replayed": require_value(
                    replay_summary,
                    "energy_proxy_routes_replayed",
                    "locked_replay.summary",
                ),
                "energy_proxy_unique_series_replays": require_value(
                    replay_summary,
                    "energy_proxy_unique_series_replays",
                    "locked_replay.summary",
                ),
                "replay_chain_sha256": require_value(replay_summary, "replay_chain_sha256", "locked_replay.summary"),
            },
            "claim_boundary": require_value(replay, "evidence_boundary", "locked_replay"),
        },
        {
            "proof_id": "eia_prospective_router",
            "title": "Frozen EIA prospective router",
            "evidence_class": "prospective_protocol",
            "attained_maturity_level": 1,
            "target_maturity_level": 4,
            "status": require_value(eia, "state", "eia_prospective_router"),
            "facts": {
                "first_allowed_target_date": require_value(
                    eia,
                    "first_allowed_target_date",
                    "eia_prospective_router",
                ),
                "prediction_count": require_value(eia, "prediction_count", "eia_prospective_router"),
                "settlement_count": require_value(eia, "settlement_count", "eia_prospective_router"),
                "promotion_evaluation_complete": require_value(
                    eia,
                    "promotion_evaluation_complete",
                    "eia_prospective_router",
                ),
                "preliminary_30_days_ready": require_value(
                    eia_gates,
                    "preliminary_30_days_ready",
                    "eia_prospective_router.sample_gates",
                ),
                "confirmatory_90_days_ready": require_value(
                    eia_gates,
                    "confirmatory_90_days_ready",
                    "eia_prospective_router.sample_gates",
                ),
                "durability_180_days_ready": require_value(
                    eia_gates,
                    "durability_180_days_ready",
                    "eia_prospective_router.sample_gates",
                ),
            },
            "claim_boundary": require_value(eia, "claim_boundary", "eia_prospective_router"),
        },
        {
            "proof_id": "mda_synthetic_feasibility_v1",
            "title": "MDA mapping synthetic feasibility v1",
            "evidence_class": "frozen_synthetic_benchmark",
            "attained_maturity_level": 2,
            "status": "gate_failed_preserved",
            "facts": {
                "fixture_count": require_value(mda_v1_counts, "total", "mda_feasibility_v1.fixture_counts"),
                "candidate_micro_f1": require_value(
                    mda_v1_candidate,
                    "micro_f1",
                    "mda_feasibility_v1.candidate",
                ),
                "candidate_unsupported_mapping_rate": require_value(
                    mda_v1_candidate,
                    "unsupported_mapping_rate",
                    "mda_feasibility_v1.candidate",
                ),
                "micro_f1_delta_over_best_baseline": require_value(
                    mda_v1_gate,
                    "micro_f1_delta_over_best_baseline",
                    "mda_feasibility_v1.gate",
                ),
                "gate_passed": require_value(mda_v1_gate, "passed", "mda_feasibility_v1.gate"),
            },
            "claim_boundary": require_value(mda_v1, "claim_boundary", "mda_feasibility_v1"),
        },
        {
            "proof_id": "mda_open_set_v2",
            "title": "MDA mapping independent open-set v2",
            "evidence_class": "frozen_synthetic_benchmark",
            "attained_maturity_level": 2,
            "status": "safer_unsupported_behavior_but_gate_failed",
            "facts": {
                "fixture_count": require_value(mda_v2_counts, "total", "mda_open_set_v2.fixture_counts"),
                "candidate_micro_f1": require_value(
                    mda_v2_candidate,
                    "micro_f1",
                    "mda_open_set_v2.candidate",
                ),
                "supported_coverage": require_value(
                    mda_v2_candidate,
                    "supported_coverage",
                    "mda_open_set_v2.candidate",
                ),
                "unsupported_mapping_rate": require_value(
                    mda_v2_candidate,
                    "unsupported_mapping_rate",
                    "mda_open_set_v2.candidate",
                ),
                "micro_f1_delta_over_best_baseline": require_value(
                    mda_v2_gate,
                    "micro_f1_delta_over_best_baseline",
                    "mda_open_set_v2.gate",
                ),
                "gate_passed": require_value(mda_v2_gate, "passed", "mda_open_set_v2.gate"),
            },
            "claim_boundary": require_value(mda_v2, "claim_boundary", "mda_open_set_v2"),
        },
        {
            "proof_id": "faa_sdr_frozen_10k",
            "title": "FAA SDR frozen 10,000-report triage benchmark",
            "evidence_class": "source_conditioned_frozen_holdout",
            "attained_maturity_level": 3,
            "status": "completed_candidate_not_promoted",
            "facts": {
                "holdout_rows": require_value(faa_splits, "holdout_rows", "faa_sdr_10k.splits"),
                "holdout_unique_keys": require_value(
                    faa_splits,
                    "holdout_unique_keys",
                    "faa_sdr_10k.splits",
                ),
                "development_key_overlap": int(
                    require_value(faa_splits, "base_holdout_key_overlap", "faa_sdr_10k.splits")
                )
                + int(require_value(faa_splits, "router_holdout_key_overlap", "faa_sdr_10k.splits")),
                "scenario_model_evaluations": require_value(
                    faa_execution,
                    "scenario_model_evaluations",
                    "faa_sdr_10k.execution",
                ),
                "candidate_macro_f1": require_value(faa_candidate, "macro_f1", "faa_sdr_10k.candidate"),
                "strongest_baseline": faa_baseline_name,
                "strongest_baseline_macro_f1": require_value(
                    faa_baseline,
                    "macro_f1",
                    "faa_sdr_10k.strongest_baseline",
                ),
                "multiplicity_adjusted_primary_improvement": require_value(
                    faa_gate,
                    "multiplicity_adjusted_primary_improvement",
                    "faa_sdr_10k.promotion_gate",
                ),
                "candidate_promoted": require_value(
                    faa_gate,
                    "candidate_promoted",
                    "faa_sdr_10k.promotion_gate",
                ),
                "rolls_royce_exploratory_rows": require_value(
                    faa_rolls,
                    "rows",
                    "faa_sdr_10k.rolls_royce_exploratory",
                ),
                "receipt_sha256": require_value(faa, "receipt_sha256", "faa_sdr_10k"),
            },
            "claim_boundary": require_value(faa, "claim_boundary", "faa_sdr_10k"),
        },
        {
            "proof_id": "funding_reviewer_gate",
            "title": "Funding-package language and secret scan",
            "evidence_class": "review_packaging_control",
            "attained_maturity_level": 1,
            "status": "clear" if bool(reviewer.get("reviewer_gate_clear")) else "blocked",
            "facts": {
                "reviewer_gate_clear": require_value(reviewer, "reviewer_gate_clear", "reviewer_gate"),
                "markdown_file_count": require_value(
                    reviewer_summary,
                    "markdown_file_count",
                    "reviewer_gate.summary",
                ),
                "unsafe_claim_count": require_value(
                    reviewer_summary,
                    "unsafe_claim_count",
                    "reviewer_gate.summary",
                ),
                "unsafe_secret_count": require_value(
                    reviewer_summary,
                    "unsafe_secret_count",
                    "reviewer_gate.summary",
                ),
            },
            "claim_boundary": "A clear packaging scan means the scanned text passed configured claim and secret rules. It is not scientific, legal, agency, security, or funding approval.",
        },
    ]

    claim_controls = {
        "currently_supported": [
            "The repository contains implemented and tested evidence-building infrastructure.",
            "The locked sweep is a source-conditioned replay with named baselines, wins, and non-wins.",
            "The MDA v1 and v2 synthetic promotion gates failed and the negative results are preserved.",
            "The frozen FAA SDR 10,000-report benchmark completed and did not promote the hybrid candidate.",
            "The EIA prospective protocol is frozen and operational but has not produced an eligible prediction or settlement in this snapshot.",
            "A prior external proof packet reports all copied artifact hashes verified.",
        ],
        "blocked_without_new_evidence": {
            "level_5_or_independent_validation": True,
            "field_validation": not bool(replay_gates.get("field_validation_claim_allowed")),
            "realized_or_fixed_dollar_savings": not bool(
                replay_gates.get("real_dollar_savings_claim_allowed")
                or replay_gates.get("fixed_dollar_delta_sale_claim_allowed")
            ),
            "production_readiness": True,
            "government_or_regulatory_approval": True,
            "universal_model_superiority": True,
            "profitable_live_trading": True,
            "patent_validity_scope_or_infringement": True,
        },
    }

    context = {
        "schema": "quant_hub_reviewer_context.v1",
        "generated_utc": now_utc(),
        "identity": identity,
        "mission": "Make LumenCore reviewable through bounded claims, reproducible measurements, preserved failures, and explicit human authority.",
        "current_evidence_posture": {
            "highest_repository_wide_supported_level": require_value(
                maturity_policy,
                "current_repository_wide_level",
                "lexicon.level_policy",
            ),
            "level_5_attained": require_value(maturity_policy, "level_5_attained", "lexicon.level_policy"),
            "level_5_gate": require_value(maturity_policy, "level_5_gate", "lexicon.level_policy"),
            "summary": "Level 3 source-conditioned replay is supported. Level 4 prospective evidence is still waiting for eligible EIA forecasts and settlements. Level 5 independent external validation has not been attained.",
        },
        "proof_cards": proof_cards,
        "claim_controls": claim_controls,
        "human_authority_policy": human_policy,
        "reviewer_decision_map": [
            {
                "decision": "Verify custody",
                "evidence": "Rehash the prior packet artifacts against its manifest and compare the source receipt in this context.",
                "remaining_gate": "Independent re-verification of the final packet after this context is staged.",
            },
            {
                "decision": "Assess quantitative evidence",
                "evidence": "Inspect the locked replay ledger, route-level baselines, wins, non-wins, and replay chain.",
                "remaining_gate": "Independent held-out data and an externally accepted metric.",
            },
            {
                "decision": "Assess falsification discipline",
                "evidence": "Review the preserved MDA v1 and v2 failed promotion gates and abstention behavior.",
                "remaining_gate": "An authoritative external corpus and independent evaluation owner.",
            },
            {
                "decision": "Assess prospective readiness",
                "evidence": "Verify the frozen EIA protocol, scheduler receipts, and zero-count waiting state.",
                "remaining_gate": "30-, 90-, and 180-day prospective settlement gates.",
            },
            {
                "decision": "Assess economic relevance",
                "evidence": "Use only technical deltas that an external owner accepts under a named operating metric.",
                "remaining_gate": "Buyer-owned assumptions, measurement period, counterfactual, and signed result receipt.",
            },
            {
                "decision": "Assess intellectual-property support",
                "evidence": "Counsel must use the official filed claims and specification plus dated, access-controlled evidence.",
                "remaining_gate": "Attorney-controlled claim chart; this public context contains no private patent-vault content.",
            },
        ],
        "next_validation_actions": [
            {
                "priority": 1,
                "action": "Keep the frozen EIA prospective router running without changing its promotion protocol.",
                "success_receipt": "Hashed predictions, settlements, and preregistered 30/90/180-day gate outputs.",
            },
            {
                "priority": 2,
                "action": "Secure one independent evaluator with held-out operational data and a pre-agreed metric.",
                "success_receipt": "Named evaluator, data boundary, protocol, acceptance metric, date, and signed or attributable result.",
            },
            {
                "priority": 3,
                "action": "Run MDA mapping only against an authoritative external corpus under a new preregistration.",
                "success_receipt": "Frozen external corpus hash, split, baselines, abstention policy, and independent score receipt.",
            },
            {
                "priority": 4,
                "action": "Translate technical deltas into economics only with a named buyer-side owner and bounded assumptions.",
                "success_receipt": "Accepted counterfactual, unit economics, sensitivity range, and no realized-savings language before measurement.",
            },
            {
                "priority": 5,
                "action": "Have patent counsel compare official filed claims with the filed specification and later dated concepts.",
                "success_receipt": "Counsel-controlled claim chart and a decision on amendment, continuation, continuation-in-part, or separate filing strategy.",
            },
        ],
        "patent_boundary": require_value(lexicon, "patent_boundary", "lexicon"),
        "public_private_boundary": require_value(lexicon, "public_private_boundary", "lexicon"),
        "known_limitations": [
            "Repeated route comparisons are not automatically statistically independent experiments.",
            "Source-conditioned replay does not equal a prospective field trial.",
            "A benchmark champion is conditional on its dataset, split, metric, baseline set, and run.",
            "Estimated economic value surfaces are prioritization aids, not realized savings or valuation evidence.",
            "A clear reviewer-language scan does not imply scientific, legal, security, agency, or funding approval.",
        ],
        "reproducibility_entrypoints": [
            "code/ops/BUILD_QUANT_HUB_REVIEWER_CONTEXT.py",
            "code/ops/BUILD_LOCKED_SOURCE_BASELINE_REPLAY_SWEEP.py",
            "code/eia_grid_prospective_router_ops.py",
            "code/mda_control_mapping_feasibility.py",
            "code/mda_control_mapping_open_set_benchmark.py",
            "code/ops/STAGE_EXTERNAL_PROOF_VAULT.py",
            "tests/test_quant_hub_reviewer_context.py",
            "tests/test_locked_source_baseline_replay_sweep.py",
            "tests/test_eia_grid_prospective_router_ops.py",
            "tests/test_mda_control_mapping_feasibility.py",
            "tests/test_mda_control_mapping_open_set_benchmark.py",
            "tests/test_external_proof_vault.py",
        ],
        "source_artifacts": receipts,
        "source_input_chain_sha256": input_chain_sha256,
        "outputs": {
            "machine_readable": repo_path(OUT_JSON),
            "dashboard_mirror": repo_path(DASHBOARD_JSON),
            "reviewer_markdown": repo_path(OUT_MD),
        },
    }
    assert_public_safe(context)
    return context


def render_markdown(context: dict[str, Any]) -> str:
    posture = require_dict(context, "current_evidence_posture", "context")
    lines = [
        "# Quant Hub Reviewer Context",
        "",
        f"Generated UTC: `{context['generated_utc']}`",
        "",
        "## Identity",
        "",
        f"- Repository: `{context['identity']['repository_display_name']}`",
        f"- Technical platform: `{context['identity']['technical_platform']}`",
        f"- Quantitative lane: `{context['identity']['quantitative_evidence_lane']}`",
        f"- Orchestration layer: `{context['identity']['orchestration_context_layer']}`",
        f"- Custody layer: `{context['identity']['proof_custody_layer']}`",
        f"- External gate: `{context['identity']['external_validation_gate']}`",
        "",
        "## Current Evidence Posture",
        "",
        f"- Highest repository-wide supported maturity: `Level {posture['highest_repository_wide_supported_level']}`",
        f"- Level 5 attained: `{str(posture['level_5_attained']).lower()}`",
        f"- Summary: {posture['summary']}",
        "",
        "Maturity is claim-specific. It is not a product-readiness, agency-approval, patent, security, or valuation grade.",
        "",
        "## Evidence Cards",
        "",
        "| Evidence | Class | Level | Status | Selected facts |",
        "|---|---|---:|---|---|",
    ]
    for card in context["proof_cards"]:
        selected = ", ".join(f"{key}={value}" for key, value in list(card["facts"].items())[:5])
        lines.append(
            f"| {card['title']} | `{card['evidence_class']}` | {card['attained_maturity_level']} | "
            f"`{card['status']}` | {selected} |"
        )

    lines.extend(
        [
            "",
            "## Supported Statements",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in context["claim_controls"]["currently_supported"])
    lines.extend(["", "## Blocked Claims", ""])
    for claim, blocked in context["claim_controls"]["blocked_without_new_evidence"].items():
        lines.append(f"- `{claim}`: `{'blocked' if blocked else 'not blocked'}`")

    lines.extend(["", "## Reviewer Decision Path", ""])
    for row in context["reviewer_decision_map"]:
        lines.append(f"### {row['decision']}")
        lines.append("")
        lines.append(f"Evidence: {row['evidence']}")
        lines.append("")
        lines.append(f"Remaining gate: {row['remaining_gate']}")
        lines.append("")

    lines.extend(["## Next Validation Actions", ""])
    for row in context["next_validation_actions"]:
        lines.append(f"{row['priority']}. {row['action']}")
        lines.append(f"   Required receipt: {row['success_receipt']}")

    lines.extend(
        [
            "",
            "## Human Authority",
            "",
        ]
    )
    for action, allowed in context["human_authority_policy"].items():
        lines.append(f"- `{action}`: `{str(allowed).lower()}`")

    lines.extend(
        [
            "",
            "## Patent And Privacy Boundary",
            "",
            context["patent_boundary"],
            "",
            context["public_private_boundary"],
            "",
            "## Source Chain",
            "",
            f"Input chain SHA-256: `{context['source_input_chain_sha256']}`",
            "",
        ]
    )
    for row in context["source_artifacts"]:
        lines.append(f"- `{row['path']}` | `{row['sha256']}` | `{row['bytes']}` bytes")
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_outputs(
    context: dict[str, Any],
    *,
    output_json: Path = OUT_JSON,
    dashboard_json: Path = DASHBOARD_JSON,
    output_markdown: Path = OUT_MD,
) -> None:
    assert_public_safe(context)
    write_json(output_json, context)
    write_json(dashboard_json, context)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(render_markdown(context), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the public-safe Quant Hub reviewer context.")
    parser.add_argument("--check", action="store_true", help="Validate and print the context without writing outputs.")
    args = parser.parse_args()
    context = build_context()
    if not args.check:
        write_outputs(context)
    print(
        json.dumps(
            {
                "schema": context["schema"],
                "highest_supported_level": context["current_evidence_posture"][
                    "highest_repository_wide_supported_level"
                ],
                "level_5_attained": context["current_evidence_posture"]["level_5_attained"],
                "proof_card_count": len(context["proof_cards"]),
                "source_input_chain_sha256": context["source_input_chain_sha256"],
                "written": not args.check,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
