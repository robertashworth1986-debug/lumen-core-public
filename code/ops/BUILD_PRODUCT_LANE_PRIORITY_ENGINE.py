from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "product_lane_priority_v1.json"
OUT_JSON = ROOT / "dashboard" / "data" / "product_lane_priority_engine_20260718.json"
LATEST_OUT_JSON = ROOT / "out" / "ops" / "product_lane_priority_engine_latest.json"
OUT_MD = ROOT / "docs" / "PRODUCT_LANE_PRIORITY_ENGINE_2026-07-18.md"
MINDWISE_MD = ROOT / "docs" / "MINDWISE_PAID_DESIGN_PARTNER_PILOT_2026-07-18.md"
MINDWISE_EMAIL = ROOT / "docs" / "MINDWISE_DESIGN_PARTNER_FOLLOWUP_EMAIL_2026-07-18.txt"
BUNDLE_MANIFEST = ROOT / "docs" / "receipts" / "PRODUCT_LANE_PRIORITY_BUNDLE_MANIFEST_2026-07-18.json"
LATEST_BUNDLE_MANIFEST = (
    ROOT / "out" / "ops" / "product_lane_priority_bundle_manifest_latest.json"
)
MINDWISE_DEMO_FEED = ROOT / "dashboard" / "data" / "mindwise_healthcare_candidate_feed_20260718.json"
PILOT_CONFIG = ROOT / "config" / "prooflock_opportunity_ops_pilot_v1.json"
HYPERCORE_PROTOCOL = ROOT / "config" / "hypercore_v8_validation_protocol_v1.json"
HYPERCORE_SYNTHETIC_PREFLIGHT = (
    ROOT
    / "dashboard"
    / "evidence"
    / "hypercore"
    / "HYPERCORE_V8_SYNTHETIC_PREFLIGHT_2026-08-02.json"
)
HARMONIC_V6_BENCHMARK = (
    ROOT
    / "clean_data"
    / "LumenLab__reports_benchmark_scores_v6.csv__14afe85295.csv"
)
HARMONIC_V6_WINS = (
    ROOT
    / "clean_data"
    / "LumenLab__reports_harmonic_wins_v6.csv__eef2674289.csv"
)
HARMONIC_V6_SOURCE = (
    ROOT
    / "data"
    / "World model lab script"
    / "Harmonic vs backprop script.txt"
)
HARMONIC_FAIR_SYNTHETIC_SUMMARY = ROOT / "out" / "fair_benchmark" / "summary.json"
HARMONIC_FAIR_REAL_SUMMARY = (
    ROOT
    / "out"
    / "real_data_fair_benchmark"
    / "20260505T072405Z"
    / "summary.json"
)
WHITEHOLE_AUDIT = ROOT / "docs" / "WHITEHOLE_WHITEHOLELAB_AUDIT_2026-08-02.md"
GOLDEN_REPLAY = (
    ROOT
    / "dashboard"
    / "data"
    / "prooflock_opportunity_ops_golden_replay_v1.json"
)

LOCAL_ONLY_HISTORICAL_INPUTS = (
    HARMONIC_V6_BENCHMARK,
    HARMONIC_V6_WINS,
    HARMONIC_V6_SOURCE,
    HARMONIC_FAIR_SYNTHETIC_SUMMARY,
    HARMONIC_FAIR_REAL_SUMMARY,
)

RUN_IDS = (
    "20260505T082948Z",
    "20260505T104706Z",
    "20260505T121657Z",
    "20260511T175644Z",
    "20260526T050639Z",
)
RUN_ROOT = ROOT / "dashboard" / "evidence" / "runs"
RAW_RUN_ROOT = ROOT / "out" / "master_universe_v2"
HEALTHCARE_FEED = ROOT / "out" / "ops" / "healthcare_grants_engine" / "healthcare_website_feed_latest.json"

BOUNDARY = (
    "Product-lane priority engine. Scores are a transparent founder strategy heuristic, not market valuation, "
    "patentability, customer acceptance, award probability, field validation, or guaranteed revenue."
)

PRODUCTIZATION_PROFILES: dict[str, dict[str, str]] = {
    "prooflock_opportunity_ops": {
        "stage": "PAID_PROOF_SPRINT_SCOPE_READY_HUMAN_APPROVAL_REQUIRED",
        "minimum_honest_sale": (
            "A fixed-scope proof sprint measuring one buyer-selected opportunity workflow; "
            "no eligibility guarantee, legal advice, certification, send, or final submission."
        ),
        "next_gate": (
            "Buyer approves the workflow, permitted sources, baseline, sample rule, acceptance "
            "criteria, price, recipient, and exact outbound message."
        ),
        "next_owner_action": (
            "Select one truthful buyer workflow and approve or reject the bounded proof-sprint scope."
        ),
    },
    "prooflock_evidence_router_api": {
        "stage": "TECHNICAL_CO_DESIGN_ONLY",
        "minimum_honest_sale": (
            "A paid receipt-schema, abstention-contract, and train-only feature design sprint; "
            "no routing-superiority or award-probability promise."
        ),
        "next_gate": (
            "Rebuild every feature from information available at decision time, preregister the "
            "comparison, and pass prospective abstention and receipt tests."
        ),
        "next_owner_action": (
            "Choose a buyer-authorized decision workflow and freeze its source and abstention contract."
        ),
    },
    "energy_forecast_validation": {
        "stage": "VALIDATION_SETUP_ONLY",
        "minimum_honest_sale": (
            "A paid protocol-freeze and independent-reproduction setup for a buyer-selected energy "
            "forecasting question; no superiority, savings, or deployment claim."
        ),
        "next_gate": (
            "Complete the preregistered prospective sample, settle actuals, compare frozen baselines, "
            "and obtain independent protocol-matched reproduction."
        ),
        "next_owner_action": (
            "Keep collecting sealed predictions and actuals without tuning on prospective outcomes."
        ),
    },
    "hypercore_readonly_resilience_evaluation": {
        "stage": "OFFLINE_EVALUATION_SETUP_ONLY",
        "minimum_honest_sale": (
            "A buyer-authorized offline resilience-evaluation design using approved historical data; "
            "no production actuation, outage reduction, or realized-savings claim."
        ),
        "next_gate": (
            "Run the frozen chronology-safe protocol on buyer-authorized data, pass falsification and "
            "power gates, and obtain independent reproduction before external validation language."
        ),
        "next_owner_action": (
            "Identify a lawful read-only dataset owner and approve only the offline evaluation scope."
        ),
    },
    "lumascout_ar_intelligence": {
        "stage": "FORWARD_OUTCOME_STUDY_REQUIRED",
        "minimum_honest_sale": (
            "No product offer yet; at most a buyer-approved forward study protocol with explicit "
            "abstention and outcome definitions."
        ),
        "next_gate": (
            "Repair internal evidence coverage, then complete a prospectively frozen forward outcome study."
        ),
        "next_owner_action": "Repair the failing typed-evidence contracts before buyer outreach.",
    },
    "guarded_market_research": {
        "stage": "PAPER_RESEARCH_PROTOCOL_ONLY",
        "minimum_honest_sale": (
            "A paper-only regime-diagnostics protocol and replay report using permitted buyer data; "
            "historical WhiteHoleLab ranks are excluded from alpha, profitability, live-capital, or "
            "investment-advice claims."
        ),
        "next_gate": (
            "Repair the WhiteHoleLab ticker-alias, manifest-completeness, and state-consistency defects "
            "in a governed working copy, then pass a prospectively frozen, leakage-controlled, "
            "cost-aware comparison against named baselines and independent review."
        ),
        "next_owner_action": (
            "Keep capital disconnected, preserve the historical archive, and freeze one buyer-authorized "
            "paper-regime research question before any rerun."
        ),
    },
    "xr_comfort_governor": {
        "stage": "RESEARCH_PROTOCOL_ONLY",
        "minimum_honest_sale": (
            "A non-medical research protocol or usability-study design; no clinical, safety, or "
            "comfort-improvement claim."
        ),
        "next_gate": (
            "Complete ethics-appropriate prospective usability testing with predefined outcomes and exclusions."
        ),
        "next_owner_action": "Define the non-medical study population, outcomes, and stop conditions.",
    },
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def write_latest_aliases(
    payload: dict[str, Any], manifest: dict[str, Any]
) -> None:
    write_json(LATEST_OUT_JSON, payload)
    write_json(LATEST_BUNDLE_MANIFEST, manifest)


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_pilot_config() -> dict[str, Any]:
    config = read_json(PILOT_CONFIG)
    if config.get("schema") != "prooflock_opportunity_ops_pilot_config_v1":
        raise ValueError("ProofLock pilot config is missing or uses the wrong schema")
    required_sections = {
        "minimum_sample",
        "permitted_sources",
        "prohibited_inputs",
        "deliverables",
        "exclusions",
        "event_schema",
        "receipt_schema",
        "acceptance_metrics",
        "acceptance_thresholds",
        "raci",
        "retention_and_security",
        "support_boundary",
        "pricing",
        "human_gates",
    }
    missing = sorted(required_sections - set(config))
    if missing:
        raise ValueError(f"ProofLock pilot config missing sections: {missing}")
    if config["pricing"].get("founder_approved") is not False:
        raise ValueError("Pilot pricing must remain unapproved until exact scope review")
    return config


def load_candidate_commercial_terms() -> dict[str, Any]:
    protocol = read_json(HYPERCORE_PROTOCOL)
    boundary = protocol.get("commercial_boundary")
    if not isinstance(boundary, dict):
        raise ValueError("HyperCore protocol is missing its commercial boundary")

    fee = boundary.get("candidate_fee_usd")
    duration = boundary.get("candidate_duration_business_days")
    if not isinstance(fee, int) or fee <= 0:
        raise ValueError("Candidate fee must be a positive integer")
    if not isinstance(duration, int) or duration <= 0:
        raise ValueError("Candidate duration must be a positive integer")
    if fee % 2:
        raise ValueError("Candidate fee must support exact 50/50 payment terms")
    if boundary.get("fee_status") != "candidate_not_committed":
        raise ValueError("Candidate fee must remain uncommitted")
    if boundary.get("external_send_allowed") is not False:
        raise ValueError("Commercial boundary must fail closed for external send")
    if boundary.get("contract_or_price_acceptance_proven") is not False:
        raise ValueError("Commercial boundary cannot imply buyer price acceptance")

    return {
        "candidate_fixed_fee_usd": fee,
        "candidate_kickoff_deposit_usd": fee // 2,
        "candidate_delivery_balance_usd": fee // 2,
        "duration_business_days": duration,
        "price_status": str(boundary["fee_status"]),
        "external_send_allowed": False,
        "buyer_price_acceptance_proven": False,
        "source_protocol": str(HYPERCORE_PROTOCOL.relative_to(ROOT)).replace("\\", "/"),
    }


def build_golden_replay(config: dict[str, Any]) -> dict[str, Any]:
    genesis = "0" * 64
    fixtures = [
        {
            "opportunity_id": "SYNTH-QUALIFIED",
            "decision": "QUALIFIED_FOR_BUYER_REVIEW",
            "blockers": [],
            "evidence": {
                "eligibility_rule": "synthetic_entity_type_allowed",
                "deadline_state": "synthetic_open_verified",
                "source_state": "synthetic_official_fixture",
            },
        },
        {
            "opportunity_id": "SYNTH-DISQUALIFIED",
            "decision": "DISQUALIFIED",
            "blockers": ["synthetic_entity_type_not_eligible"],
            "evidence": {
                "eligibility_rule": "synthetic_entity_type_excluded",
                "deadline_state": "synthetic_open_verified",
                "source_state": "synthetic_official_fixture",
            },
        },
        {
            "opportunity_id": "SYNTH-INSUFFICIENT",
            "decision": "ABSTAIN_INSUFFICIENT_EVIDENCE",
            "blockers": ["missing_synthetic_deadline_receipt"],
            "evidence": {
                "eligibility_rule": "synthetic_rule_present",
                "deadline_state": "unverified",
                "source_state": "synthetic_incomplete_fixture",
            },
        },
    ]
    events: list[dict[str, Any]] = []
    previous = genesis
    for index, fixture in enumerate(fixtures, start=1):
        event = {
            "event_id": f"GOLDEN-{index:03d}",
            "event_utc": f"2026-07-18T00:0{index}:00Z",
            "opportunity_id": fixture["opportunity_id"],
            "source_id": "synthetic_fixture_v1",
            "action_type": "eligibility_and_deadline_review",
            "actor_role": "system_draft_for_human_review",
            "evidence_sha256": stable_hash(fixture["evidence"]),
            "decision": fixture["decision"],
            "blockers": fixture["blockers"],
            "human_authority_state": "not_requested",
            "previous_event_sha256": previous,
        }
        event["event_sha256"] = stable_hash(event)
        previous = event["event_sha256"]
        events.append(event)

    receipt = {
        "protocol_id": config["protocol_id"],
        "event_count": len(events),
        "genesis_sha256": genesis,
        "terminal_event_sha256": previous,
        "chain_valid": True,
    }
    receipt["receipt_sha256"] = stable_hash(receipt)
    replay = {
        "schema": "prooflock_opportunity_ops_golden_replay_v1",
        "protocol_id": config["protocol_id"],
        "fixture_data_class": "synthetic_no_phi_no_credentials",
        "events": events,
        "receipt": receipt,
        "boundary": (
            "This replay proves deterministic decision-state and receipt-chain "
            "behavior for synthetic fixtures only. It does not prove eligibility, "
            "customer outcomes, awards, savings, or production readiness."
        ),
    }
    replay["replay_sha256"] = stable_hash(replay)
    return replay


def verify_golden_replay(replay: dict[str, Any]) -> bool:
    replay_without_hash = dict(replay)
    observed_replay_hash = replay_without_hash.pop("replay_sha256", None)
    if observed_replay_hash != stable_hash(replay_without_hash):
        return False

    events = replay.get("events")
    receipt = replay.get("receipt")
    if not isinstance(events, list) or not isinstance(receipt, dict):
        return False
    previous = str(receipt.get("genesis_sha256") or "")
    if previous != "0" * 64:
        return False
    for event_value in events:
        if not isinstance(event_value, dict):
            return False
        event = dict(event_value)
        observed_hash = event.pop("event_sha256", None)
        if event.get("previous_event_sha256") != previous:
            return False
        if observed_hash != stable_hash(event):
            return False
        previous = str(observed_hash)
    receipt_without_hash = dict(receipt)
    observed_receipt_hash = receipt_without_hash.pop("receipt_sha256", None)
    return (
        receipt.get("event_count") == len(events)
        and receipt.get("terminal_event_sha256") == previous
        and receipt.get("chain_valid") is True
        and observed_receipt_hash == stable_hash(receipt_without_hash)
    )


def file_receipt(path: Path) -> dict[str, Any]:
    relative_path = str(path.relative_to(ROOT)).replace("\\", "/")
    if not path.is_file():
        return {"path": relative_path, "exists": False, "bytes": 0, "sha256": None}
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {
        "path": relative_path,
        "exists": True,
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def build_whiteholelab_remediation_gate() -> dict[str, Any]:
    required_markers = (
        "WhiteHole is useful as historical custody",
        "Neither currently establishes forecasting",
        "ticker-key fallback",
        "manifest.json",
        "ignores the emitted fracture state",
        "Keep WhiteHole frozen as an archive.",
    )
    try:
        text = WHITEHOLE_AUDIT.read_text(encoding="utf-8")
    except OSError:
        text = ""
    marker_checks = {marker: marker in text for marker in required_markers}
    audit_current = WHITEHOLE_AUDIT.is_file() and all(marker_checks.values())
    defects = [
        {
            "id": "ticker_alias_fallback_noop",
            "severity": "high",
            "historical_source": "C:/WhiteHoleLab/engine/whitehole_universe.py:185",
            "observed_behavior": "A missing exact Kraken ticker key enters a no-op loop and the instrument is silently skipped.",
            "required_fix": "Resolve aliases from the AssetPairs metadata and emit an explicit unmapped-pair receipt instead of silently continuing.",
            "required_test": "Fixture exact, aliased, and unmapped ticker keys and assert deterministic coverage accounting.",
        },
        {
            "id": "universe_manifest_omits_report",
            "severity": "high",
            "historical_source": "C:/WhiteHoleLab/engine/whitehole_universe.py:285",
            "observed_behavior": "The saved manifest is written before report.pdf and therefore omits the report receipt.",
            "required_fix": "Generate every output before sealing the manifest, then verify every packaged file against the saved manifest.",
            "required_test": "Build a temporary proof pack and assert exact manifest-to-archive file and SHA-256 parity.",
        },
        {
            "id": "current_state_ignores_fracture_flag",
            "severity": "high",
            "historical_source": "C:/WhiteHoleLab/engine/whitehole_universe.py:213",
            "observed_behavior": "The current state is recomputed from coherence alone even when the metric function marks the observation FRACTURE.",
            "required_fix": "Use the emitted regime state as the single classification source and fail closed on contradictory labels.",
            "required_test": "Fixture a high-coherence fractured observation and require FRACTURE rather than FLOW.",
        },
    ]
    return {
        "schema": "whiteholelab_remediation_gate_v1",
        "status": (
            "REMEDIATION_SPEC_READY_ARCHIVE_FROZEN"
            if audit_current
            else "BLOCKED_AUDIT_MISSING_OR_STALE"
        ),
        "audit_current": audit_current,
        "audit_receipt": file_receipt(WHITEHOLE_AUDIT),
        "audit_marker_checks": marker_checks,
        "historical_archive_root": "C:/WhiteHoleLab/WhiteHole",
        "historical_engine_root": "C:/WhiteHoleLab/engine",
        "archive_mutation_allowed": False,
        "legacy_site_deploy_allowed": False,
        "current_product_lane": "guarded_market_research",
        "current_use": "Historical custody, reproducibility context, and descriptive diagnostic lineage only.",
        "implementation_target": "A governed working copy with source/hash lineage; never the frozen archive.",
        "defect_count": len(defects),
        "defects": defects,
        "required_validation": [
            "freeze metric definitions and calibration data before examining holdout outcomes",
            "compare next-window realized volatility or drawdown against named naive and EWMA baselines",
            "settle a preregistered prospective sample with multiple-testing control and after-cost reporting",
            "obtain independent protocol-matched reproduction before external performance language",
        ],
        "performance_claim_allowed": False,
        "alpha_claim_allowed": False,
        "external_send_allowed": False,
        "promotion_gate_passed": False,
    }


def build_bundle_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    paths = (
        CONFIG,
        Path(__file__).resolve(),
        OUT_JSON,
        OUT_MD,
        MINDWISE_MD,
        MINDWISE_EMAIL,
        ROOT / "dashboard" / "js" / "luma_healthcare_grants_embed.js",
        ROOT / "dashboard" / "embed" / "healthcare_grants_widget_example.html",
        ROOT / "dashboard" / "embed" / "mindwise_premium_flow_demo.html",
        ROOT / "code" / "ops" / "HEALTHCARE_WEBSITE_EMBED_PLAYBOOK.md",
        ROOT / "tests" / "test_product_lane_priority_engine.py",
        MINDWISE_DEMO_FEED,
        PILOT_CONFIG,
        HYPERCORE_PROTOCOL,
        HYPERCORE_SYNTHETIC_PREFLIGHT,
        GOLDEN_REPLAY,
        WHITEHOLE_AUDIT,
    )
    receipts = [file_receipt(path) for path in paths]
    manifest: dict[str, Any] = {
        "schema": "product_lane_priority_bundle_manifest_v1",
        "generated_utc": payload["generated_utc"],
        "product_lane_priority_sha256": payload["product_lane_priority_sha256"],
        "all_artifacts_present": all(receipt["exists"] for receipt in receipts),
        "artifact_count": len(receipts),
        "artifacts": receipts,
        "excluded_local_only_inputs": [
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in LOCAL_ONLY_HISTORICAL_INPUTS
        ],
        "public_reproducibility_status": (
            "The public bundle excludes non-versioned local historical inputs. "
            "They cannot be treated as reproducible public evidence."
        ),
        "boundary": (
            "File receipts prove byte identity and presence only. They do not prove eligibility, correctness, "
            "independent validation, customer acceptance, award probability, or commercial value."
        ),
    }
    manifest["manifest_payload_sha256"] = stable_hash(manifest)
    return manifest


def parse_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except (OSError, csv.Error):
        return []


def audit_harmonic_backprop_claim() -> dict[str, Any]:
    benchmark_rows = read_csv_rows(HARMONIC_V6_BENCHMARK)
    wins_rows = read_csv_rows(HARMONIC_V6_WINS)
    try:
        source = HARMONIC_V6_SOURCE.read_text(encoding="utf-8")
    except OSError:
        source = ""
    source_lower = source.lower()

    harmonic_wins = sum(
        1
        for row in benchmark_rows
        if parse_float(row.get("harmonic_beats_backprop")) == 1.0
    )
    harmonic_beats_baseline = sum(
        1
        for row in benchmark_rows
        if parse_float(row.get("harmonic_beats_baseline")) == 1.0
    )
    harmonic_beats_both = sum(
        1
        for row in benchmark_rows
        if parse_float(row.get("harmonic_beats_backprop")) == 1.0
        and parse_float(row.get("harmonic_beats_baseline")) == 1.0
    )
    negative_backprop_r2 = sum(
        1
        for row in benchmark_rows
        if (parse_float(row.get("r2_backprop")) or 0.0) < 0.0
    )
    period_equals_series_length = sum(
        1
        for row in benchmark_rows
        if (
            parse_float(row.get("period_est")) is not None
            and parse_float(row.get("n_points")) is not None
            and math.isclose(
                float(parse_float(row.get("period_est"))),
                float(parse_float(row.get("n_points"))),
                rel_tol=0.0,
                abs_tol=1e-9,
            )
        )
    )

    full_series_refit = all(
        marker in source_lower
        for marker in (
            "fit full and evaluate last holdout segment",
            "hm_full = harmonic_fit_predict(y)",
            "bp_full = backprop_fit_predict(y)",
            "hm_test = hm_full[-split:]",
            "bp_test = bp_full[-split:]",
        )
    )
    train_predictions_unused_for_scoring = all(
        marker in source_lower
        for marker in (
            "hm_train = harmonic_fit_predict(train_y)",
            "bp_train = backprop_fit_predict(train_y)",
            "hm_test = hm_full[-split:]",
            "bp_test = bp_full[-split:]",
        )
    )
    target_scaling_detected = any(
        marker in source_lower
        for marker in (
            "standardscaler().fit_transform(y",
            "minmaxscaler().fit_transform(y",
            "y_scaler",
        )
    )

    synthetic_fair = read_json(HARMONIC_FAIR_SYNTHETIC_SUMMARY)
    real_fair = read_json(HARMONIC_FAIR_REAL_SUMMARY)
    required_files_present = all(
        path.is_file()
        for path in (
            HARMONIC_V6_BENCHMARK,
            HARMONIC_V6_WINS,
            HARMONIC_V6_SOURCE,
            HARMONIC_FAIR_SYNTHETIC_SUMMARY,
            HARMONIC_FAIR_REAL_SUMMARY,
        )
    )
    historical_result_consistent = (
        len(benchmark_rows) == 400
        and harmonic_wins == 362
        and len(wins_rows) == 362
    )
    status = (
        "HISTORICAL_EXPLORATORY_ONLY_NOT_CLAIM_READY"
        if required_files_present and historical_result_consistent
        else "MISSING_OR_INCONSISTENT_SOURCE_FAIL_CLOSED"
    )

    return {
        "schema": "harmonic_backprop_legacy_claim_audit_v1",
        "status": status,
        "comparison": "harmonic_vs_backprop",
        "historical_result": {
            "benchmark_rows": len(benchmark_rows),
            "harmonic_beats_backprop_rows": harmonic_wins,
            "wins_file_rows": len(wins_rows),
            "harmonic_beats_baseline_rows": harmonic_beats_baseline,
            "harmonic_beats_both_rows": harmonic_beats_both,
            "negative_backprop_r2_rows": negative_backprop_r2,
            "period_est_equals_series_length_rows": period_equals_series_length,
            "historical_result_consistent": historical_result_consistent,
        },
        "protocol_findings": {
            "full_series_refit_before_holdout_scoring_detected": full_series_refit,
            "train_only_predictions_unused_for_test_scoring_detected": (
                train_predictions_unused_for_scoring
            ),
            "target_scaling_detected_for_mlp": target_scaling_detected,
            "capacity_matched_comparator_documented": False,
            "chronology_safe_out_of_sample_evaluation": False,
            "independent_reproduction": False,
            "issues": [
                "Models are refit on the full series before the final segment is scored, so the labeled holdout is not chronology-safe out-of-sample evidence.",
                "The backprop MLP normalizes time inputs but does not scale the target, and comparator capacity parity is not documented.",
                "Negative backprop R-squared values and period estimates equal to full series length require comparator and feature audits.",
            ],
        },
        "bounded_corrective_runs": {
            "synthetic_dataset_count": len(synthetic_fair.get("datasets", [])),
            "real_eia_series_count": len(real_fair.get("datasets", {})),
            "boundary": (
                "The corrective summaries are self-authored bounded diagnostics over four synthetic "
                "datasets and four EIA series. They do not establish general superiority or independent validation."
            ),
        },
        "external_claim_allowed": False,
        "allowed_description": (
            "A historical internal exploratory artifact records 362 harmonic wins in 400 comparisons; "
            "a source audit found protocol defects that block external performance use."
        ),
        "blocked_description": (
            "Do not present 362/400 as current, prospective, independently validated, or general "
            "harmonic superiority over backpropagation."
        ),
        "required_next_gate": (
            "Preregister and run a chronology-safe, capacity-matched, target-scaled prospective comparison "
            "against frozen naive, statistical, and neural baselines, then obtain independent reproduction."
        ),
        "source_receipts": [
            file_receipt(path)
            for path in (
                HARMONIC_V6_BENCHMARK,
                HARMONIC_V6_WINS,
                HARMONIC_V6_SOURCE,
                HARMONIC_FAIR_SYNTHETIC_SUMMARY,
                HARMONIC_FAIR_REAL_SUMMARY,
            )
        ],
    }


def build_productization_matrix(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for lane in ranked:
        lane_id = str(lane.get("id") or "")
        profile = PRODUCTIZATION_PROFILES.get(lane_id)
        internal_gate = bool(lane.get("internal_evidence_gate_passed"))
        if profile is None:
            stage = "UNMAPPED_FAIL_CLOSED"
            minimum_honest_sale = "No external offer; this lane has no approved productization profile."
            next_gate = "Define and review a claim-bounded productization profile."
            next_owner_action = "Keep the lane internal until its profile and evidence gates are reviewed."
        elif not internal_gate:
            stage = "INTERNAL_EVIDENCE_REPAIR_REQUIRED"
            minimum_honest_sale = "No external offer until all required typed-evidence contracts pass."
            next_gate = str(profile["next_gate"])
            next_owner_action = str(profile["next_owner_action"])
        else:
            stage = str(profile["stage"])
            minimum_honest_sale = str(profile["minimum_honest_sale"])
            next_gate = str(profile["next_gate"])
            next_owner_action = str(profile["next_owner_action"])

        matrix.append(
            {
                "rank": lane.get("rank"),
                "lane_id": lane_id,
                "lane_name": lane.get("name"),
                "strategy_score": lane.get("strategy_score"),
                "internal_evidence_gate_passed": internal_gate,
                "validated_evidence_coverage": lane.get("validated_evidence_coverage"),
                "current_stage": stage,
                "minimum_honest_sale": minimum_honest_sale,
                "next_gate": next_gate,
                "next_owner_action": next_owner_action,
                "blocked_claims": list(lane.get("blocked_claims") or []),
                "buyer_acceptance_proven": False,
                "product_ready": False,
                "external_send_allowed": False,
            }
        )
    return matrix


def parse_utc_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_evidence_contract(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {
            "path": value,
            "required": True,
            "kind": "legacy_untyped_artifact",
            "claim_scope": "",
            "min_bytes": 1,
            "expected_schema": None,
            "required_keys": [],
            "max_age_hours": None,
            "legacy_untyped": True,
        }
    if not isinstance(value, dict):
        return {
            "path": "",
            "required": True,
            "kind": "invalid_contract",
            "claim_scope": "",
            "min_bytes": 1,
            "expected_schema": None,
            "required_keys": [],
            "max_age_hours": None,
            "legacy_untyped": False,
        }

    required_keys = value.get("required_keys")
    if not isinstance(required_keys, list):
        required_keys = []
    return {
        "path": str(value.get("path") or "").strip(),
        "required": bool(value.get("required", True)),
        "kind": str(value.get("kind") or "artifact").strip(),
        "claim_scope": str(value.get("claim_scope") or "").strip(),
        "min_bytes": value.get("min_bytes", 1),
        "expected_schema": value.get("expected_schema"),
        "required_keys": [str(item) for item in required_keys if str(item).strip()],
        "max_age_hours": value.get("max_age_hours"),
        "legacy_untyped": False,
    }


def validate_evidence_contract(value: Any, at: datetime | None = None) -> dict[str, Any]:
    at = (at or now_utc()).astimezone(timezone.utc)
    contract = normalize_evidence_contract(value)
    path_text = contract["path"]
    reasons: list[str] = []

    min_bytes = parse_float(contract["min_bytes"])
    if min_bytes is None or min_bytes < 1:
        reasons.append("contract_invalid_min_bytes")
        min_bytes = 1.0
    max_age_hours = parse_float(contract["max_age_hours"])
    if contract["max_age_hours"] is not None and (
        max_age_hours is None or max_age_hours <= 0
    ):
        reasons.append("contract_invalid_max_age_hours")
        max_age_hours = None
    expected_schema = contract["expected_schema"]
    if expected_schema is not None and not isinstance(expected_schema, str):
        reasons.append("contract_invalid_expected_schema")
        expected_schema = None
    if contract["legacy_untyped"]:
        reasons.append("contract_legacy_untyped")
    if not contract["claim_scope"]:
        reasons.append("contract_missing_claim_scope")
    if not path_text:
        reasons.append("contract_missing_path")

    target: Path | None = None
    if path_text:
        try:
            target = (ROOT / path_text).resolve()
            target.relative_to(ROOT.resolve())
        except (OSError, ValueError):
            reasons.append("contract_path_outside_root")
            target = None

    exists = bool(target and target.exists())
    is_file = bool(target and target.is_file())
    size = 0
    modified_utc: str | None = None
    sha256: str | None = None
    age_hours: float | None = None
    age_source: str | None = None
    observed_schema: Any = None
    observed_keys: list[str] = []
    missing_keys: list[str] = []
    json_payload: dict[str, Any] | None = None

    if target is not None and not exists:
        reasons.append("artifact_missing")
    elif target is not None and not is_file:
        reasons.append("artifact_not_file")
    elif target is not None:
        stat = target.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        modified_utc = modified.isoformat()
        age_reference = modified
        age_source = "file_modified_utc"
        if size < min_bytes:
            reasons.append("artifact_below_min_bytes")

        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        sha256 = digest.hexdigest()

        needs_json = (
            expected_schema is not None
            or bool(contract["required_keys"])
            or target.suffix.lower() == ".json"
        )
        if needs_json:
            try:
                candidate = json.loads(target.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                reasons.append("artifact_invalid_json")
            else:
                if isinstance(candidate, dict):
                    json_payload = candidate
                    observed_schema = candidate.get("schema")
                    observed_keys = sorted(str(key) for key in candidate)
                    generated = parse_utc_datetime(candidate.get("generated_utc"))
                    if generated is not None:
                        age_reference = generated
                        age_source = "json_generated_utc"
                else:
                    reasons.append("artifact_json_not_object")

        if expected_schema is not None and json_payload is not None:
            if observed_schema != expected_schema:
                reasons.append("artifact_schema_mismatch")
        if contract["required_keys"] and json_payload is not None:
            missing_keys = sorted(set(contract["required_keys"]) - set(json_payload))
            if missing_keys:
                reasons.append("artifact_missing_required_keys")
        else:
            missing_keys = []

        if max_age_hours is not None:
            age_hours = (at - age_reference).total_seconds() / 3600
            if age_hours < -0.25:
                reasons.append("artifact_timestamp_in_future")
            elif age_hours > max_age_hours:
                reasons.append("artifact_stale")
    contract_complete = not any(reason.startswith("contract_") for reason in reasons)
    valid = not reasons
    return {
        "path": path_text,
        "required": contract["required"],
        "kind": contract["kind"],
        "claim_scope": contract["claim_scope"],
        "contract_complete": contract_complete,
        "valid": valid,
        "status": "valid" if valid else "invalid",
        "reasons": reasons,
        "exists": exists,
        "is_file": is_file,
        "bytes": size,
        "min_bytes": int(min_bytes),
        "sha256": sha256,
        "modified_utc": modified_utc,
        "expected_schema": expected_schema,
        "observed_schema": observed_schema,
        "required_keys": contract["required_keys"],
        "missing_required_keys": missing_keys,
        "observed_keys": observed_keys,
        "max_age_hours": max_age_hours,
        "age_hours": round(age_hours, 4) if age_hours is not None else None,
        "age_source": age_source,
    }


def audit_run(run_id: str) -> dict[str, Any]:
    run_dir = RUN_ROOT / run_id
    summary = read_json(run_dir / "summary.json")
    scorecard_path = run_dir / "UNDENIABLE_SCORECARD_V2.md"
    scorecard = scorecard_path.read_text(encoding="utf-8", errors="replace") if scorecard_path.exists() else ""

    model_rows: Counter[str] = Counter()
    valid_rows: Counter[str] = Counter()
    error_rows: Counter[str] = Counter()
    results_path = run_dir / "results.csv"
    if results_path.exists():
        with results_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                model = str(row.get("model") or "unknown")
                model_rows[model] += 1
                if parse_float(row.get("rmse")) is not None:
                    valid_rows[model] += 1
                else:
                    error_rows[model] += 1

    failures = {
        model: {
            "invalid_rows": int(error_rows[model]),
            "total_rows": int(model_rows[model]),
        }
        for model in sorted(model_rows)
        if error_rows[model]
    }
    all_models_complete = bool(model_rows) and not failures
    raw_dir = RAW_RUN_ROOT / run_id / "raw"
    raw_count = len(list(raw_dir.glob("*.csv"))) if raw_dir.exists() else 0
    scorecard_calls_walk_forward = "walk-forward" in scorecard.lower()

    return {
        "run_id": run_id,
        "datasets_succeeded": int(summary.get("n_datasets_succeeded") or 0),
        "attempted_datasets": int(summary.get("n_datasets_in_universe") or 0),
        "models_reported": sorted(model_rows),
        "model_count": len(model_rows),
        "all_models_complete": all_models_complete,
        "model_failures": failures,
        "raw_csv_count": raw_count,
        "dashboard_manifest_note": (
            "Dashboard copy hashes six summary artifacts; raw CSVs remain in the canonical out/master_universe_v2 run."
        ),
        "evaluation_design": "single_chronological_80_20_holdout",
        "scorecard_calls_method_walk_forward": scorecard_calls_walk_forward,
        "method_language_status": "stale_overstatement" if scorecard_calls_walk_forward else "bounded",
        "reviewer_use": (
            "bounded_exploratory_reference"
            if all_models_complete
            else "blocked_from_comparative_headline"
        ),
    }


def audit_healthcare_feed(at: datetime) -> dict[str, Any]:
    feed = read_json(HEALTHCARE_FEED)
    generated_text = str(feed.get("generated_utc") or "")
    generated: datetime | None = None
    try:
        generated = datetime.fromisoformat(generated_text.replace("Z", "+00:00"))
    except ValueError:
        pass
    if generated is not None and generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    age_hours = (at - generated).total_seconds() / 3600 if generated is not None else None
    records = feed.get("records") if isinstance(feed.get("records"), list) else []
    is_fresh = age_hours is not None and 0 <= age_hours <= 24
    return {
        "path": str(HEALTHCARE_FEED.relative_to(ROOT)).replace("\\", "/"),
        "generated_utc": generated_text,
        "record_count": len(records),
        "freshness_sla_hours": 24,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
        "freshness_label_allowed": is_fresh,
        "eligibility_label_allowed": False,
        "submission_ready_label_allowed": False,
        "status": "fresh" if is_fresh else "stale_or_unverifiable",
        "boundary": (
            "Freshness applies only to the candidate source feed. Relevance scores do not establish applicant "
            "eligibility, current requirements, submission readiness, or award probability."
        ),
    }


def build_mindwise_demo_feed() -> dict[str, Any]:
    source = read_json(HEALTHCARE_FEED)
    source_records = source.get("records") if isinstance(source.get("records"), list) else []
    records = [row for row in source_records[:6] if isinstance(row, dict)]

    def closes_within(row: dict[str, Any], days: int) -> bool:
        value = parse_float(row.get("days_to_close"))
        return value is not None and 0 <= value <= days

    snapshot: dict[str, Any] = {
        "schema": "mindwise_healthcare_candidate_feed_demo_v1",
        "generated_utc": source.get("generated_utc"),
        "source": source.get("source", {}),
        "summary": {
            "close_7_days": sum(1 for row in records if closes_within(row, 7)),
            "close_14_days": sum(1 for row in records if closes_within(row, 14)),
            "urgent_or_expedited_review": sum(
                1
                for row in records
                if str(row.get("action") or "").upper()
                in {"URGENT_REVIEW", "EXPEDITED_REVIEW"}
            ),
            "snapshot_records": len(records),
        },
        "records": records,
        "boundary": (
            "Frozen demonstration snapshot from a source-linked candidate feed. Scores and queue labels reflect "
            "configured relevance and urgency only; they do not establish organizational eligibility, current "
            "requirements, submission readiness, or award probability."
        ),
    }
    snapshot["snapshot_payload_sha256"] = stable_hash(snapshot)
    return snapshot


def rank_lanes(
    config: dict[str, Any],
    at: datetime | None = None,
) -> list[dict[str, Any]]:
    at = at or now_utc()
    weights = config.get("weights") if isinstance(config.get("weights"), dict) else {}
    if round(sum(float(value) for value in weights.values()), 8) != 100:
        raise ValueError("product-lane weights must sum to 100")

    ranked: list[dict[str, Any]] = []
    for lane in config.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        scores = lane.get("scores") if isinstance(lane.get("scores"), dict) else {}
        missing_dimensions = sorted(set(weights) - set(scores))
        if missing_dimensions:
            raise ValueError(f"{lane.get('id')} missing score dimensions: {missing_dimensions}")
        weighted = sum(float(scores[key]) * float(weight) for key, weight in weights.items()) / 100
        evidence_checks = [
            validate_evidence_contract(value, at)
            for value in lane.get("evidence_paths", [])
        ]
        required_checks = [item for item in evidence_checks if item["required"]]
        validated_count = sum(1 for item in required_checks if item["valid"])
        evidence_coverage = (
            validated_count / len(required_checks)
            if required_checks
            else 0.0
        )
        internal_evidence_gate_passed = bool(required_checks) and all(
            item["valid"] for item in required_checks
        )
        evidence_blockers = [
            {
                "path": item["path"],
                "reasons": item["reasons"],
            }
            for item in required_checks
            if not item["valid"]
        ]
        buyer_gate_status = (
            "requires_external_buyer_validation"
            if internal_evidence_gate_passed
            else "blocked_internal_evidence"
        )
        ranked.append(
            {
                **lane,
                "strategy_score": round(weighted, 2),
                "evidence_coverage": round(evidence_coverage, 4),
                "validated_evidence_coverage": round(evidence_coverage, 4),
                "validated_evidence_count": validated_count,
                "required_evidence_count": len(required_checks),
                "evidence_checks": evidence_checks,
                "internal_evidence_gate_passed": internal_evidence_gate_passed,
                "buyer_readiness_gate": {
                    "passed": False,
                    "status": buyer_gate_status,
                    "internal_evidence_gate_passed": internal_evidence_gate_passed,
                    "evidence_blockers": evidence_blockers,
                    "next_required_validation": lane.get("first_validation"),
                    "boundary": (
                        "Internal artifact validation cannot establish buyer acceptance, "
                        "organizational eligibility, external validation, or commercial readiness."
                    ),
                },
            }
        )
    ranked.sort(key=lambda row: (-float(row["strategy_score"]), str(row["id"])))
    for index, lane in enumerate(ranked, start=1):
        lane["rank"] = index
    return ranked


def mindwise_pilot(config: dict[str, Any]) -> dict[str, Any]:
    commercial_terms = load_candidate_commercial_terms()
    return {
        "name": "ProofLock Opportunity Operations - 30-day paid pilot",
        "buyer_selected": False,
        "buyer": None,
        "commercial_entry_offer": {
            "name": "Opportunity-operations proof sprint",
            "duration": f"{commercial_terms['duration_business_days']} business days",
            "buyer_state": "historical_warm_reactivation_candidate_recent_interest_unconfirmed",
            **commercial_terms,
            "deliverables": [
                "source and eligibility register for one buyer-selected workflow",
                "pursue/no-pursue decision brief with unresolved facts named",
                "reviewer-ready package outline",
                "attachment and blocker ledger",
                "replayable receipt for each material decision",
            ],
            "commercial_gate": (
                "Scope, source permissions, baseline, acceptance criteria, candidate fixed price, "
                "payment terms, recipient, and exact outbound message require written approval "
                "before kickoff or send."
            ),
            "boundary": (
                "The sprint is a bounded paid service offer, not evidence of buyer acceptance, "
                "customer outcomes, award probability, savings, or production readiness."
            ),
        },
        "status": config["status"],
        "protocol_id": config["protocol_id"],
        "duration_days": config["duration_days"],
        "scope_boundary": config["scope_boundary"],
        "minimum_sample": config["minimum_sample"],
        "permitted_sources": config["permitted_sources"],
        "prohibited_inputs": config["prohibited_inputs"],
        "deliverables": config["deliverables"],
        "exclusions": config["exclusions"],
        "event_schema": config["event_schema"],
        "receipt_schema": config["receipt_schema"],
        "commercial_posture": (
            "Paid pilot after exact buyer scope, baseline, acceptance thresholds, "
            "data terms, price, and recipient are approved."
        ),
        "week_1_baseline": [
            "Measure current time from opportunity discovery to pursue/no-pursue decision.",
            "Measure current time from pursue decision to reviewer-ready draft.",
            "Count eligibility reversals, missing attachments, and missed internal review dates.",
            "Freeze source permissions, eligibility rules, metric denominators, thresholds, roles, and human gates.",
        ],
        "weeks_2_to_4": [
            "Refresh permitted opportunity sources and rank candidates with evidence links.",
            "Generate source-grounded draft structures and an attachment/blocker ledger.",
            "Route unresolved facts to named owners; abstain instead of guessing.",
            "Emit a replayable receipt for every shortlist, draft, and preflight decision.",
        ],
        "acceptance_metrics": config["acceptance_metrics"],
        "acceptance_thresholds": config["acceptance_thresholds"],
        "raci": config["raci"],
        "retention_and_security": config["retention_and_security"],
        "support_boundary": config["support_boundary"],
        "pricing": config["pricing"],
        "human_gates": config["human_gates"],
        "go_no_go": (
            "Convert only when the frozen sample rule is met and the buyer confirms "
            "that every accepted metric passes its prospectively approved threshold. "
            "Otherwise stop, extend under a documented alternate sample rule, or abstain."
        ),
    }


def build_payload(at: datetime | None = None) -> dict[str, Any]:
    at = at or now_utc()
    config = read_json(CONFIG)
    pilot_config = load_pilot_config()
    golden_replay = build_golden_replay(pilot_config)
    if not verify_golden_replay(golden_replay):
        raise ValueError("ProofLock golden replay failed receipt-chain verification")
    ranked = rank_lanes(config, at)
    run_audits = [audit_run(run_id) for run_id in RUN_IDS]
    comparable = [row for row in run_audits if row["all_models_complete"]]
    best_exploratory = max(comparable, key=lambda row: row["datasets_succeeded"], default={})
    pilot = mindwise_pilot(pilot_config)
    feed_audit = audit_healthcare_feed(at)
    harmonic_backprop_audit = audit_harmonic_backprop_claim()
    whiteholelab_remediation = build_whiteholelab_remediation_gate()
    productization_matrix = build_productization_matrix(ranked)
    allowed_now = [
        "working grant-ranking, draft-assembly, preflight, and receipt components exist",
        "five historical benchmark runs and raw source directories exist",
        "the 673-dataset run is a bounded exploratory single-holdout reference",
        "a paid design-partner pilot can measure workflow improvement",
    ]
    if feed_audit["freshness_label_allowed"]:
        allowed_now.append(
            "the healthcare candidate feed was refreshed within its 24-hour SLA; freshness does not establish eligibility"
        )
    if whiteholelab_remediation["audit_current"]:
        allowed_now.append(
            "WhiteHole provides historical custody context and WhiteHoleLab provides descriptive diagnostic lineage only"
        )
    blocked_now = [
        "organizational eligibility from relevance scores alone",
        "urgent or priority labels as authorization to apply or submit",
        "prospective router superiority until train-only features pass",
        "field validation or realized savings",
        "guaranteed awards or autonomous final submission",
        "patentability",
        "the historical 362/400 harmonic-versus-backprop result as current, prospective, independently validated, or general superiority evidence",
        "WhiteHoleLab coherence scores or watchlist ranks as alpha, expected return, forecasting skill, or buyer outcome evidence",
        "deployment of the historical WhiteHoleLab website or mutation of the frozen WhiteHole archive",
    ]
    if not feed_audit["freshness_label_allowed"]:
        blocked_now.insert(0, "current-feed language until the candidate feed is refreshed within the freshness SLA")

    payload: dict[str, Any] = {
        "schema": "product_lane_priority_engine_v1",
        "generated_utc": at.isoformat(),
        "boundary": BOUNDARY,
        "evidence_contract_version": "typed_evidence_contract_v1",
        "weights": config.get("weights", {}),
        "ranking": ranked,
        "productization_matrix": productization_matrix,
        "recommendation": {
            "commercial_lane": ranked[0]["id"] if ranked else None,
            "commercial_offer": ranked[0]["offer"] if ranked else None,
            "commercial_stage": (
                productization_matrix[0]["current_stage"]
                if productization_matrix
                else "NO_LANE_FAIL_CLOSED"
            ),
            "minimum_honest_sale": (
                productization_matrix[0]["minimum_honest_sale"]
                if productization_matrix
                else "No external offer."
            ),
            "technical_wedge": "prooflock_evidence_router_api",
            "technical_wedge_boundary": (
                "The defensible target is not generic grant search or AI writing. It is a constrained router that "
                "uses train-only or source-available features, abstains when eligibility or evidence gates fail, "
                "and emits replayable policy/source receipts. Patentability still requires a dedicated search."
            ),
            "first_design_partner": "unselected_requires_current_validated_target",
            "why_now": (
                (
                    "Typed internal evidence contracts pass for the top lane. Buyer selection, "
                    "workflow baseline, acceptance thresholds, eligibility review, and measured "
                    "pilot outcomes remain external gates."
                )
                if ranked and ranked[0]["internal_evidence_gate_passed"]
                else (
                    "The top strategy lane has unresolved typed-evidence blockers. Repair those "
                    "internal artifacts before selecting a buyer or describing the offer as ready."
                )
            ),
        },
        "evidence_audit": {
            "runs": run_audits,
            "best_bounded_exploratory_run": best_exploratory.get("run_id"),
            "best_bounded_exploratory_dataset_count": best_exploratory.get("datasets_succeeded"),
            "router_risk": (
                "The historical meta-router extracts features from each full series, including the benchmark test "
                "window. Cross-dataset CV does not remove that within-series look-ahead. Rebuild features from each "
                "training window as train-only inputs before making prospective routing claims."
            ),
            "latest_run_blocker": (
                "Run 20260526T050639Z is blocked from comparative headline use because i_sarima has no valid RMSE "
                "on all 1,118 datasets while the scorecard still describes a classical comparison."
            ),
            "healthcare_feed": feed_audit,
            "harmonic_backprop_legacy_claim": harmonic_backprop_audit,
            "whiteholelab_remediation": whiteholelab_remediation,
        },
        "market_boundary": {
            "crowded_features": [
                "grant matching and tracking",
                "AI-assisted proposal drafting",
                "grant database search and APIs",
                "grantmaker workflow and review management",
            ],
            "official_product_sources_checked_2026_07_18": [
                "https://www.instrumentl.com/product-overview",
                "https://grantable.co/",
                "https://ops.opengrants.io/api-docs",
                "https://www.submittable.com/solutions/grants",
            ],
            "inference": (
                "Generic grant finding/filling is not a defensible category claim. Lead with evidence-bound "
                "eligibility, deterministic abstention, deadline controls, and replayable submission receipts."
            ),
        },
        "prooflock_opportunity_ops_pilot": pilot,
        "mindwise_pilot": pilot,
        "pilot_protocol_receipts": {
            "config_path": str(PILOT_CONFIG.relative_to(ROOT)).replace("\\", "/"),
            "config_sha256": stable_hash(pilot_config),
            "golden_replay_path": str(GOLDEN_REPLAY.relative_to(ROOT)).replace("\\", "/"),
            "golden_replay_sha256": golden_replay["replay_sha256"],
            "golden_replay_verified": True,
            "golden_replay_event_count": len(golden_replay["events"]),
            "golden_replay_decisions": [
                event["decision"] for event in golden_replay["events"]
            ],
            "boundary": golden_replay["boundary"],
        },
        "claim_controls": {
            "allowed_now": allowed_now,
            "blocked_now": blocked_now,
        },
    }
    payload["product_lane_priority_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Product Lane Priority Engine",
        "",
        f"Generated: `{payload['generated_utc']}`",
        "",
        f"> {payload['boundary']}",
        "",
        "## Decision",
        "",
        "Package **ProofLock Opportunity Operations** as the first human-approved paid proof-sprint candidate. Use the **ProofLock Evidence Router API** as a narrower technical co-design wedge. No lane is product-ready or authorized for external send by this artifact.",
        "",
        "## Ranked Lanes",
        "",
        "| Rank | Lane | Strategy score | Validated evidence | Buyer gate | First validation |",
        "|---:|---|---:|---:|---|---|",
    ]
    for lane in payload["ranking"]:
        lines.append(
            f"| {lane['rank']} | {lane['name']} | {lane['strategy_score']:.2f} | "
            f"{lane['validated_evidence_coverage'] * 100:.0f}% | "
            f"{lane['buyer_readiness_gate']['status']} | {lane['first_validation']} |"
        )

    lines.extend(
        [
            "",
            "## Productization Matrix",
            "",
            "| Rank | Lane | Current stage | Internal evidence | Product ready | External send | Next gate |",
            "|---:|---|---|---|---|---|---|",
        ]
    )
    for lane in payload["productization_matrix"]:
        lines.append(
            f"| {lane['rank']} | {lane['lane_name']} | `{lane['current_stage']}` | "
            f"{str(lane['internal_evidence_gate_passed']).lower()} | "
            f"{str(lane['product_ready']).lower()} | "
            f"{str(lane['external_send_allowed']).lower()} | {lane['next_gate']} |"
        )

    audit = payload["evidence_audit"]
    feed = audit["healthcare_feed"]
    harmonic = audit["harmonic_backprop_legacy_claim"]
    whitehole = audit["whiteholelab_remediation"]
    historical = harmonic["historical_result"]
    lines.extend(
        [
            "",
            "## Evidence Audit",
            "",
            f"- Best bounded exploratory run: `{audit['best_bounded_exploratory_run']}` with `{audit['best_bounded_exploratory_dataset_count']}` datasets.",
            f"- Latest-run blocker: {audit['latest_run_blocker']}",
            f"- Router blocker: {audit['router_risk']}",
            f"- Healthcare candidate feed: `{feed['status']}`; age `{feed['age_hours']}` hours; freshness label allowed `{str(feed['freshness_label_allowed']).lower()}`; eligibility label allowed `{str(feed['eligibility_label_allowed']).lower()}`.",
            f"- Feed boundary: {feed['boundary']}",
            "",
            "## Legacy Harmonic/Backprop Claim Gate",
            "",
            f"- Historical internal result: `{historical['harmonic_beats_backprop_rows']}` harmonic wins in `{historical['benchmark_rows']}` comparisons.",
            f"- Claim status: `{harmonic['status']}`.",
            f"- External claim allowed: `{str(harmonic['external_claim_allowed']).lower()}`.",
            f"- Protocol finding: `{historical['negative_backprop_r2_rows']}` negative backprop R-squared rows and `{historical['period_est_equals_series_length_rows']}` rows where the estimated period equals the full series length.",
            f"- Boundary: {harmonic['blocked_description']}",
            f"- Next gate: {harmonic['required_next_gate']}",
            "",
            "## WhiteHoleLab Remediation Gate",
            "",
            f"- Status: `{whitehole['status']}`.",
            f"- Product lane: `{whitehole['current_product_lane']}`.",
            f"- Frozen archive mutation allowed: `{str(whitehole['archive_mutation_allowed']).lower()}`.",
            f"- Legacy site deployment allowed: `{str(whitehole['legacy_site_deploy_allowed']).lower()}`.",
            f"- Performance or alpha claim allowed: `{str(whitehole['performance_claim_allowed']).lower()}`.",
            f"- Documented implementation defects: `{whitehole['defect_count']}`.",
            f"- Current use: {whitehole['current_use']}",
            "",
            "## Commercial Wedge",
            "",
            payload["recommendation"]["technical_wedge_boundary"],
            "",
            "The first recurring product is an organization subscription for monitored opportunities, controlled collaboration, evidence storage, and preflight. Final certifications and submissions remain with the authorized human.",
            "",
            "## Buyer-Neutral Pilot",
            "",
            f"- Scope: {payload['mindwise_pilot']['scope_boundary']}",
            f"- Commercial posture: {payload['mindwise_pilot']['commercial_posture']}",
            f"- Go/no-go: {payload['mindwise_pilot']['go_no_go']}",
            "",
            "Acceptance metrics:",
        ]
    )
    for item in payload["mindwise_pilot"]["acceptance_metrics"]:
        lines.append(
            f"- **{item['metric']}**: numerator = {item['numerator']}; "
            f"denominator = {item['denominator']}"
        )
    lines.extend(
        [
            "",
            "## Claim Gates",
            "",
            "Allowed now:",
        ]
    )
    lines.extend(f"- {value}" for value in payload["claim_controls"]["allowed_now"])
    lines.extend(["", "Blocked now:"])
    lines.extend(f"- {value}" for value in payload["claim_controls"]["blocked_now"])
    lines.extend(["", "## Receipt", "", f"SHA-256: `{payload['product_lane_priority_sha256']}`"])
    return "\n".join(lines)


def render_mindwise_brief(payload: dict[str, Any]) -> str:
    pilot = payload["mindwise_pilot"]
    entry_offer = pilot["commercial_entry_offer"]
    lines = [
        "# ProofLock Opportunity Operations",
        "",
        "## Buyer-Neutral 30-Day Paid Pilot Protocol",
        "",
        "### Objective",
        "",
        "Measure whether an evidence-bound opportunity workflow can reduce administrative cycle time and package defects without making unsupported eligibility, award, or savings claims.",
        "",
        "### Boundary",
        "",
        pilot["scope_boundary"],
        "",
        "### Buyer And Commercial State",
        "",
        "- Buyer selected: `false`",
        f"- Protocol status: `{pilot['status']}`",
        f"- Pricing status: `{pilot['pricing']['status']}`",
        "- No fee, subscription price, recipient, or external communication is approved by this document.",
        "",
        "### Commercial Entry Offer",
        "",
        f"- Offer: {entry_offer['name']}",
        f"- Duration: {entry_offer['duration']}",
        f"- Candidate fixed fee: `${entry_offer['candidate_fixed_fee_usd']:,}`",
        f"- Candidate kickoff deposit: `${entry_offer['candidate_kickoff_deposit_usd']:,}`",
        f"- Candidate delivery balance: `${entry_offer['candidate_delivery_balance_usd']:,}`",
        f"- Price status: `{entry_offer['price_status']}`",
        f"- Buyer state: `{entry_offer['buyer_state']}`",
        f"- Gate: {entry_offer['commercial_gate']}",
        f"- Boundary: {entry_offer['boundary']}",
        "- Deliverables:",
    ]
    lines.extend(f"  - {item}" for item in entry_offer["deliverables"])
    lines.extend(
        [
        "",
        "### Minimum Sample",
        "",
        f"- Reviewed opportunities: `{pilot['minimum_sample']['reviewed_opportunities']}`",
        f"- Pursued packages: `{pilot['minimum_sample']['pursued_packages']}`",
        f"- Alternate rule: {pilot['minimum_sample']['alternate_sample_rule']}",
        "",
        "### Week 1: Lock the Baseline",
        "",
        ]
    )
    lines.extend(f"- {item}" for item in pilot["week_1_baseline"])
    lines.extend(["", "### Weeks 2-4: Run the Pilot", ""])
    lines.extend(f"- {item}" for item in pilot["weeks_2_to_4"])
    lines.extend(["", "### Acceptance Metrics", ""])
    lines.extend(
        (
            f"- **{item['metric']}**: numerator = {item['numerator']}; "
            f"denominator = {item['denominator']}"
        )
        for item in pilot["acceptance_metrics"]
    )
    lines.extend(
        [
            "",
            "Threshold rule:",
            "",
            f"- {pilot['acceptance_thresholds']['rule']}",
            "",
            "### Permitted Sources",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in pilot["permitted_sources"])
    lines.extend(["", "### Prohibited Inputs", ""])
    lines.extend(f"- {item}" for item in pilot["prohibited_inputs"])
    lines.extend(["", "### Deliverables", ""])
    lines.extend(f"- {item}" for item in pilot["deliverables"])
    lines.extend(["", "### Exclusions", ""])
    lines.extend(f"- {item}" for item in pilot["exclusions"])
    lines.extend(["", "### RACI", ""])
    lines.extend(f"- **{role}**: {duty}" for role, duty in pilot["raci"].items())
    lines.extend(
        [
            "",
            "### Retention And Security",
            "",
            f"- Default post-pilot retention: `{pilot['retention_and_security']['default_retention_days_after_pilot']}` days",
            f"- Deletion: {pilot['retention_and_security']['deletion_rule']}",
            f"- Access: {pilot['retention_and_security']['access_rule']}",
            f"- Incident response: {pilot['retention_and_security']['incident_rule']}",
            "",
            "### Support Boundary",
            "",
            f"- Included: {pilot['support_boundary']['included']}",
            f"- Excluded: {pilot['support_boundary']['excluded']}",
        ]
    )
    lines.extend(["", "### Human Authority Gates", ""])
    lines.extend(f"- {item}" for item in pilot["human_gates"])
    lines.extend(
        [
            "",
            "### Commercial Path",
            "",
            pilot["commercial_posture"],
            "",
            "No value, savings, performance, or price figure is quoted until a selected buyer approves the baseline inputs and prospective thresholds and the pilot produces a traceable measurement.",
            "",
            "### Golden Replay",
            "",
            f"- Verified: `{str(payload['pilot_protocol_receipts']['golden_replay_verified']).lower()}`",
            f"- Synthetic events: `{payload['pilot_protocol_receipts']['golden_replay_event_count']}`",
            f"- Replay SHA-256: `{payload['pilot_protocol_receipts']['golden_replay_sha256']}`",
            f"- Boundary: {payload['pilot_protocol_receipts']['boundary']}",
        ]
    )
    return "\n".join(lines)


def render_mindwise_email(payload: dict[str, Any]) -> str:
    pilot = payload["mindwise_pilot"]
    entry_offer = pilot["commercial_entry_offer"]
    deliverables = ", ".join(entry_offer["deliverables"])
    return "\n".join(
        [
            "DRAFT ONLY - VERIFIED WARM REACTIVATION ROUTE - EXACT SEND AND PRICE APPROVAL REQUIRED",
            "",
            "Subject: MindWise x LumenCore: 10-day paid grant-operations proof sprint",
            "",
            "Hi [Authorized MindWise contact],",
            "",
            "I appreciated your positive response to the MindWise grant-flow demo. I have since narrowed the first step so it is smaller, measurable, and easier to evaluate before either side commits to a larger implementation.",
            "",
            (
                f"I propose a paid proof sprint lasting {entry_offer['duration']} on one MindWise "
                f"opportunity workflow. The deliverables would be: {deliverables}."
            ),
            "",
            (
                f"The candidate fixed fee is ${entry_offer['candidate_fixed_fee_usd']:,}, split "
                f"into a ${entry_offer['candidate_kickoff_deposit_usd']:,} kickoff deposit and "
                f"${entry_offer['candidate_delivery_balance_usd']:,} on delivery. The price is "
                "not committed until we both approve the written scope."
            ),
            "",
            "Before work starts, we would agree the permitted sources, current baseline, acceptance criteria, deliverables, and fixed price. This first sprint would use no PHI or credentials, provide no legal advice, and make no autonomous certifications or submissions.",
            "",
            (
                "If the sprint produces enough evidence to justify a larger test, the next step would be the "
                f"buyer-approved {pilot['duration_days']}-day pilot with prospectively frozen metrics. "
                "If it does not, we stop with the completed proof packet."
            ),
            "",
            "Would you be open to a 20-minute call to choose one workflow and scope the proof sprint?",
            "",
            "Respectfully,",
            "Robert Ashworth",
        ]
    )


def main() -> int:
    payload = build_payload()
    pilot_config = load_pilot_config()
    golden_replay = build_golden_replay(pilot_config)
    if not verify_golden_replay(golden_replay):
        raise ValueError("ProofLock golden replay failed before artifact write")
    demo_feed = build_mindwise_demo_feed()
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    write_text(MINDWISE_MD, render_mindwise_brief(payload))
    write_text(MINDWISE_EMAIL, render_mindwise_email(payload))
    write_json(MINDWISE_DEMO_FEED, demo_feed)
    write_json(GOLDEN_REPLAY, golden_replay)
    manifest = build_bundle_manifest(payload)
    write_json(BUNDLE_MANIFEST, manifest)
    write_latest_aliases(payload, manifest)
    print(json.dumps({
        "output_json": str(OUT_JSON),
        "output_markdown": str(OUT_MD),
        "mindwise_brief": str(MINDWISE_MD),
        "mindwise_email_draft": str(MINDWISE_EMAIL),
        "mindwise_demo_feed": str(MINDWISE_DEMO_FEED),
        "bundle_manifest": str(BUNDLE_MANIFEST),
        "top_lane": payload["recommendation"]["commercial_lane"],
        "sha256": payload["product_lane_priority_sha256"],
        "bundle_manifest_sha256": manifest["manifest_payload_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
