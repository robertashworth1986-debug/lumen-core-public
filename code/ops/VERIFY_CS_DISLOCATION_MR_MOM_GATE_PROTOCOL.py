#!/usr/bin/env python3
"""Fail-closed validator for the CS dislocation paper preregistration.

This module validates a static JSON contract. It has no market-data, network,
paper-fill, order, credential, or trading execution capability.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = ROOT / "config" / "cs_dislocation_mr_mom_gate_paper_v1.json"

EXPECTED_SCHEMA_VERSION = "cs_dislocation_mr_mom_gate_paper_protocol.v1"
EXPECTED_PROTOCOL_ID = "CS_DISLOCATION_MR_MOM_GATE_PAPER_V1"
EXPECTED_VERSION = 1
EXPECTED_STATUS = "PRECOLLECTION_LOCKED_PAPER_ONLY"
EXPECTED_SUCCESS_LABEL = "PROSPECTIVE_PAPER_EDGE_SUPPORTED"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# Each semantic section is independently sealed here. This catches a mutation
# even if someone recomputes the self-hash and all inline binding hashes.
EXPECTED_SECTION_SHA256 = {
    "registration": "60be672e0e73363607d9cd41071d129ed9bec33950e6a3af7556609e4ed91b8d",
    "boundaries": "ee449d51b445587e25f717b225ca9e128082d05fbf63c2bd47bf97a2fcc63a06",
    "point_in_time_universe": "ae0fd3efc2310a6841654298f35d33c2fb627a50ab3f748a167da6e5af4c4bea",
    "clock_and_no_lookahead": "e1a4c4e48f45c07fde4e146f6ebc57674a78e1af07b01403793e34bb81c3c837",
    "raw_data_contract": "75ff9360830efe7a2d4f957a3c3c826d4bb52c1fca3849121016ffed510375cf",
    "primary_signal": "6159ddf8112635466f5235c8b778522de3bf4d757302d1d5fa2346e234a88de5",
    "candidate_family": "7345f0e0fb406ec4b66917cfeb9b7516316f99e1d6af10b8c0d070bd323520f0",
    "walk_forward_holdouts": "6111235edfc5eaeee456c05660bd12e40652298850506604fbc4ae93d732bbb4",
    "baselines": "ff7c96b3172202daf49a7a0bd293b2903c4816e480c9af3a33ab49af6f44ad92",
    "execution_model": "d7802a338a19005f7ac8767df42ff6d2d90fa8342498b0de59d32f101ce2b25d",
    "uncertainty_and_multiplicity": "6b955a7714084484158638d00bd17da659b6db5615eabe38ffa713b36dc7687a",
    "sample_gates": "e7b13cee450ae8c8c493d7c8250a9a2501de0e9578457a7096092ddd34a399ae",
    "promotion_policy": "7af12cc41d6b1c41b8c9b1c10dd3a87448488b016dc0638538b357d9f4f3d614",
    "kill_criteria": "494bde8f202d689fc822219857c13d824d4ae3edd5c6511ed55f72e69140c21d",
    "claim_policy": "13d74be4818d4a7109aa10ae6329402e3099d9f37e249a99f764c038a6253350",
    "reproducibility": "3d1948075019444cc041f6dd660edb2b10755d701096f5b563a45c1dd5b7a3c2",
}

EXPECTED_EXTERNAL_BINDINGS = (
    (
        "SEALED_SCIENTIFIC_AUDIT",
        "out/ops/alpha_edge_scientific_audit_20260719/"
        "ALPHA_EDGE_SCIENTIFIC_AUDIT_20260719.md",
    ),
    (
        "VALIDATOR_IMPLEMENTATION",
        "code/ops/VERIFY_CS_DISLOCATION_MR_MOM_GATE_PROTOCOL.py",
    ),
    ("DEPENDENCY_LOCK", "requirements-reviewer-ubuntu-py311.lock"),
)

EXPECTED_INLINE_BINDINGS = (
    ("SYMBOL_EXCLUSIONS", "/point_in_time_universe/exclusions"),
    ("FEE_SCHEDULE", "/execution_model/fee_model"),
    ("RAW_DATA_SCHEMA", "/raw_data_contract"),
    ("CANDIDATE_FAMILY", "/candidate_family"),
    ("RANDOM_SEED", "/registration/random_seed"),
    ("START_TIMESTAMP_T0", "/registration/t0_utc"),
)

EXPECTED_FULL_GRID = set(itertools.product((1.5, 2.0, 2.5), (1, 3), (6, 12)))
EXPECTED_ADDITIONAL_VARIANT_IDS = {
    "ablation_dislocation_only",
    "ablation_momentum_only",
    "ablation_no_cost_edge_gate",
    "ablation_no_spread_capacity_gate",
    "ablation_rank_enter_non_data_gates_removed",
    "placebo_time_shift_plus_24h",
}
EXPECTED_BASELINE_IDS = (
    "cash_zero_return",
    "equal_weight_monthly",
    "btc_buy_hold_volatility_matched",
    "cross_sectional_momentum_24h",
    "dislocation_only",
    "randomized_entry_event_matched",
)
EXPECTED_SAMPLE_GATE_IDS = (
    "INTEGRITY",
    "PRELIMINARY",
    "CONFIRMATORY",
    "DURABILITY",
)
EXPECTED_PROMOTION_GATE_IDS = (
    "ZERO_INTEGRITY_VIOLATIONS",
    "LEDGER_AND_OBSERVATION_INTEGRITY",
    "CONFIRMATORY_SAMPLE",
    "PRIMARY_ACTIVE_RETURN",
    "SHARPE_AND_SELECTION_ADJUSTMENT",
    "BASE_AND_STRESS_RETURNS",
    "COST_AND_TURNOVER",
    "DRAWDOWN_AND_CONCENTRATION",
    "CAPACITY_AND_LATENCY",
    "ABLATION_SUPERIORITY",
    "INDEPENDENT_REPRODUCTION",
)

FORBIDDEN_BOUNDARY_FLAGS = (
    "private_or_authenticated_api_allowed",
    "order_endpoint_allowed",
    "exchange_sandbox_order_allowed",
    "live_order_allowed",
    "capital_exposure_allowed",
    "margin_allowed",
    "shorting_allowed",
    "borrow_allowed",
    "funding_allowed",
    "network_contact_by_validator_allowed",
    "paper_fill_generation_by_validator_allowed",
)

# Exact recursive object schemas. No object may omit a key, add a key, or occur
# at an unregistered location.
OBJECT_KEYS: dict[str, frozenset[str]] = {
    "$": frozenset(
        {
            "schema_version",
            "protocol_id",
            "version",
            "protocol_status",
            "registration",
            "boundaries",
            "immutable_bindings",
            "point_in_time_universe",
            "clock_and_no_lookahead",
            "raw_data_contract",
            "primary_signal",
            "candidate_family",
            "walk_forward_holdouts",
            "baselines",
            "execution_model",
            "uncertainty_and_multiplicity",
            "sample_gates",
            "promotion_policy",
            "kill_criteria",
            "claim_policy",
            "reproducibility",
        }
    ),
    "$.registration": frozenset(
        {
            "frozen_at_utc",
            "t0_utc",
            "random_seed",
            "confirmatory_observations_before_t0_allowed",
            "changes_require_protocol_id",
            "cross_version_result_bridging_allowed",
            "receipt_publication",
        }
    ),
    "$.registration.receipt_publication": frozenset(
        {
            "required_before_confirmatory_collection",
            "required_medium",
            "local_mutable_file_is_sufficient",
            "attestation_status",
        }
    ),
    "$.boundaries": frozenset(
        {
            "mode",
            "asset_and_position_lane",
            "nominal_nav_usd",
            "collector_policy",
            "public_unauthenticated_market_data_only",
            "private_or_authenticated_api_allowed",
            "order_endpoint_allowed",
            "exchange_sandbox_order_allowed",
            "live_order_allowed",
            "capital_exposure_allowed",
            "margin_allowed",
            "shorting_allowed",
            "borrow_allowed",
            "funding_allowed",
            "network_contact_by_validator_allowed",
            "paper_fill_generation_by_validator_allowed",
            "execution_capability",
        }
    ),
    "$.immutable_bindings": frozenset(
        {
            "hash_algorithm",
            "canonicalization",
            "protocol_payload_hash_rule",
            "protocol_payload_sha256",
            "external_files",
            "inline_payloads",
        }
    ),
    "$.immutable_bindings.external_files[]": frozenset(
        {"role", "path", "sha256"}
    ),
    "$.immutable_bindings.inline_payloads[]": frozenset(
        {"role", "json_pointer", "sha256"}
    ),
    "$.point_in_time_universe": frozenset(
        {
            "freeze_frequency",
            "freeze_day_of_month",
            "freeze_time_utc",
            "source_snapshot",
            "information_cutoff",
            "membership_receipt_required",
            "exclusions",
            "eligibility",
            "ranking",
            "delisting",
        }
    ),
    "$.point_in_time_universe.exclusions": frozenset(
        {
            "payload_id",
            "stablecoin_base_assets",
            "fiat_base_assets",
            "leveraged_token_base_regex",
            "matching_rule",
            "changes_require_v2",
        }
    ),
    "$.point_in_time_universe.eligibility": frozenset(
        {
            "minimum_listing_age_days",
            "prior_hourly_bar_window_days",
            "minimum_hourly_bar_completeness",
            "prior_notional_volume_window_days",
            "minimum_median_daily_notional_usd",
            "prior_quoted_spread_window_days",
            "maximum_median_quoted_spread_bps",
        }
    ),
    "$.point_in_time_universe.ranking": frozenset(
        {
            "metric",
            "direction",
            "maximum_assets",
            "tie_break",
            "minimum_assets_or_cash",
            "new_assets_enter_next_monthly_freeze_only",
        }
    ),
    "$.point_in_time_universe.delisting": frozenset(
        {
            "retain_delisted_and_suspended_assets_in_history",
            "force_close_price",
            "additional_penalty_bps",
        }
    ),
    "$.clock_and_no_lookahead": frozenset(
        {
            "timezone",
            "bar_interval_minutes",
            "feature_seal_deadline_seconds_after_bar_end",
            "earliest_fill_seconds_after_bar_end",
            "fill_rule",
            "latency_stress_fill_seconds_after_bar_end",
            "latency_stress_computed_in_parallel",
            "required_timestamps",
            "source_record_hash_required",
            "completed_bars_only",
            "missing_data_backfill_into_prior_decisions_allowed",
            "revised_data_backfill_into_prior_decisions_allowed",
            "same_delayed_fill_rule_for_entries_and_exits",
        }
    ),
    "$.raw_data_contract": frozenset(
        {
            "public_market_data_only",
            "immutable_raw_snapshots_required",
            "credentials_or_account_identifiers_permitted",
            "retroactive_replacement_permitted",
            "record_hash_algorithm",
            "record_schemas",
            "timestamp_invariants",
            "unique_identifiers",
        }
    ),
    "$.raw_data_contract.record_schemas[]": frozenset(
        {"record_type", "required_fields"}
    ),
    "$.raw_data_contract.timestamp_invariants[]": frozenset(
        {"left", "operator", "right"}
    ),
    "$.primary_signal": frozenset(
        {"primary_variant_id", "regression", "dislocation", "entry", "ranking", "portfolio", "exit"}
    ),
    "$.primary_signal.regression": frozenset(
        {
            "method",
            "dependent_variable",
            "factors",
            "include_intercept",
            "trailing_training_days",
            "minimum_complete_training_hours",
            "training_ends_strictly_before_decision_bar",
        }
    ),
    "$.primary_signal.dislocation": frozenset(
        {
            "residual_sum_hours",
            "standardization_lookback_values",
            "center",
            "scale",
            "formula",
            "zero_mad_fallback",
        }
    ),
    "$.primary_signal.entry": frozenset(
        {
            "z_lte",
            "z_change_from_prior_hour_gte",
            "residual_momentum_window_hours",
            "residual_momentum_sum_gt",
            "implied_exit_z",
            "minimum_implied_move_to_round_trip_cost_multiple",
            "required_gates",
        }
    ),
    "$.primary_signal.ranking": frozenset({"metric", "direction"}),
    "$.primary_signal.portfolio": frozenset(
        {
            "maximum_positions",
            "target_nav_fraction_per_position",
            "maximum_gross_exposure_fraction",
            "leverage_allowed",
        }
    ),
    "$.primary_signal.exit": frozenset(
        {
            "first_condition_wins",
            "z_gte",
            "negative_momentum_consecutive_hours",
            "negative_momentum_window_hours",
            "maximum_hold_hours",
            "adverse_move_realized_vol_multiple",
            "realized_vol_lookback_hours",
            "completed_bars_and_delayed_fill_required",
        }
    ),
    "$.candidate_family": frozenset(
        {
            "attempt_count",
            "full_variant_count",
            "additional_test_count",
            "all_attempts_count_from_first_run",
            "failed_or_abandoned_attempts_retained",
            "historical_selection",
            "prospective_selection",
            "variants",
        }
    ),
    "$.candidate_family.historical_selection": frozenset(
        {"selection_scope", "outer_test_selected_variant_may_be_promoted"}
    ),
    "$.candidate_family.prospective_selection": frozenset(
        {"frozen_variant_id", "frozen_before_t0", "replacement_without_v2_allowed"}
    ),
    "$.candidate_family.variants[]": frozenset(
        {
            "id",
            "class",
            "entry_z_magnitude",
            "momentum_window_hours",
            "maximum_hold_hours",
            "removed_gates",
            "time_shift_hours",
            "definition",
            "promotion_eligible",
            "counts_from_first_run",
        }
    ),
    "$.walk_forward_holdouts": frozenset(
        {
            "minimum_disjoint_outer_folds",
            "train_days",
            "validation_days",
            "test_days",
            "advance_days",
            "purge_and_embargo_hours_each_boundary",
            "fit_on_train_and_validation_only",
            "outer_test_used_once",
            "minimum_oos_calendar_days_for_admissible_history",
            "minimum_closed_oos_trades_for_admissible_history",
            "below_minimum_disposition",
        }
    ),
    "$.baselines": frozenset(
        {"count", "primary_contrast_ids", "items", "secondary_contrasts_registered", "secondary_contrasts_may_promote"}
    ),
    "$.baselines.items[]": frozenset(
        {
            "id",
            "definition",
            "primary_contrast",
            "same_point_in_time_universe",
            "same_clock",
            "same_fee_slippage_model",
            "promotion_capable",
        }
    ),
    "$.execution_model": frozenset(
        {"fee_model", "slippage_model", "stress_model", "costed_events", "required_reports", "capacity"}
    ),
    "$.execution_model.fee_model": frozenset(
        {"per_side_rule", "minimum_per_side_fee_bps", "public_fee_snapshot_frozen_at_t0", "applies_to_every_turnover_event"}
    ),
    "$.execution_model.slippage_model": frozenset(
        {
            "buy_reference",
            "sell_reference",
            "per_side_rule",
            "minimum_per_side_slippage_bps",
            "adverse_markout_percentile",
            "adverse_markout_horizon_seconds",
            "adverse_markout_training_window_days",
            "training_only",
            "impact_model",
        }
    ),
    "$.execution_model.stress_model": frozenset(
        {"fee_multiplier", "observed_spread_multiplier", "slippage_multiplier", "fill_delay_seconds_after_bar_end", "computed_in_parallel"}
    ),
    "$.execution_model.capacity": frozenset(
        {
            "maximum_order_usd",
            "maximum_trailing_five_minute_median_dollar_volume_fraction",
            "maximum_visible_depth_fraction",
            "visible_depth_band_bps",
            "order_size_rule",
            "missing_depth_disposition",
            "all_orders_must_pass_for_evidence",
            "capacity_curve_nav_usd",
        }
    ),
    "$.uncertainty_and_multiplicity": frozenset(
        {
            "primary_analysis_unit",
            "bootstrap",
            "fwer",
            "secondary",
            "deflated_sharpe",
            "optional_stopping_allowed",
            "unregistered_subgroup_promotion_allowed",
            "planned_interim_count",
            "early_promotion_allowed",
        }
    ),
    "$.uncertainty_and_multiplicity.bootstrap": frozenset(
        {"method", "resamples", "expected_block_length_days", "interval_sides", "confidence_level", "seed_derivation", "hac_sensitivity_lag_days"}
    ),
    "$.uncertainty_and_multiplicity.fwer": frozenset(
        {"variant_count", "primary_baseline_count", "contrast_count", "preferred_method", "alpha", "fallback_method", "fallback_only_if_preferred_unavailable", "fallback_substitution_must_be_disclosed"}
    ),
    "$.uncertainty_and_multiplicity.secondary": frozenset(
        {"method", "maximum_q", "may_promote_claim"}
    ),
    "$.uncertainty_and_multiplicity.deflated_sharpe": frozenset(
        {"attempted_variant_count", "minimum_probability_of_skill"}
    ),
    "$.sample_gates": frozenset(
        {"count", "thresholds_may_relax", "short_regime_cell_collection_extends_to_days", "gates"}
    ),
    "$.sample_gates.gates[]": frozenset(
        {
            "id",
            "minimum_days",
            "minimum_closes",
            "minimum_active_days",
            "minimum_assets_observed",
            "regime_cell_count",
            "minimum_closes_per_regime_cell",
            "independent_reproduction_required",
            "additional_requirement",
            "allowed_label",
        }
    ),
    "$.promotion_policy": frozenset(
        {"required_gate_count", "all_gates_must_pass", "gates"}
    ),
    "$.promotion_policy.gates[]": frozenset({"number", "id", "conditions"}),
    "$.promotion_policy.gates[].conditions[]": frozenset(
        {"metric", "operator", "value", "unit"}
    ),
    "$.kill_criteria": frozenset(
        {"immediate_invalidation", "operational_pause", "harm_stop", "planned_interim", "terminal_retirement"}
    ),
    "$.kill_criteria.immediate_invalidation": frozenset({"action", "triggers"}),
    "$.kill_criteria.operational_pause": frozenset(
        {"action", "consecutive_days", "observation_completeness_below", "p95_decision_seal_latency_above_seconds", "lifecycle_mismatch_above_fraction"}
    ),
    "$.kill_criteria.harm_stop": frozenset(
        {"action", "prospective_drawdown_reaches_fraction"}
    ),
    "$.kill_criteria.planned_interim": frozenset(
        {"maximum_count", "timing_rule", "minimum_days", "minimum_closes", "allowed_purposes", "futility_conditional_power_below", "futility_cash_mean_return_95pct_upper_lte", "early_promotion_allowed"}
    ),
    "$.kill_criteria.terminal_retirement": frozenset(
        {"action", "triggers", "modification_requires_new_version", "modification_requires_new_prospective_sample"}
    ),
    "$.claim_policy": frozenset(
        {
            "declared_result_label",
            "allowed_success_label",
            "maximum_claim_label",
            "success_requires_all_11_promotion_gates",
            "bounded_to_dimensions",
            "live_alpha_claim_allowed",
            "institutional_capacity_claim_allowed",
            "large_fund_claim_allowed",
            "universal_superiority_claim_allowed",
            "profitable_live_claim_allowed",
            "prohibited_claim_labels",
        }
    ),
    "$.reproducibility": frozenset(
        {
            "required_packet_contents",
            "offline_reproduction_required",
            "network_access_required_for_reproduction",
            "account_credentials_required_for_reproduction",
            "independent_reproduction_required_for_durability",
            "decision_reproduction_tolerance",
            "daily_net_return_reproduction_tolerance_bps_per_day",
        }
    ),
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_number(value: str) -> None:
    raise ValueError(f"non-finite JSON number is prohibited: {value}")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_nonfinite_number,
    )
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return value


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or UTC_TIMESTAMP_RE.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError(f"invalid JSON pointer: {pointer!r}")
    value = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and token in value:
            value = value[token]
            continue
        if isinstance(value, list) and token.isdigit():
            index = int(token)
            if index < len(value):
                value = value[index]
                continue
        raise ValueError(f"JSON pointer does not resolve: {pointer}")
    return value


def protocol_signing_payload(protocol: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(protocol)
    bindings = payload.get("immutable_bindings")
    if not isinstance(bindings, dict):
        raise ValueError("immutable_bindings must be an object")
    bindings["protocol_payload_sha256"] = None
    return payload


def protocol_payload_sha256(protocol: dict[str, Any]) -> str:
    return canonical_sha256(protocol_signing_payload(protocol))


def _walk_structure(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        expected = OBJECT_KEYS.get(path)
        if expected is None:
            errors.append(f"unregistered object location: {path}")
            return
        actual = set(value)
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errors.append(f"missing keys at {path}: {', '.join(missing)}")
        if extra:
            errors.append(f"extra keys at {path}: {', '.join(extra)}")
        for key, child in value.items():
            _walk_structure(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for child in value:
            _walk_structure(child, f"{path}[]", errors)


def _safe_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _resolve_repo_path(root: Path, relative_path: Any) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("binding path must be nonempty text")
    candidate_text = Path(relative_path)
    if candidate_text.is_absolute() or candidate_text.drive:
        raise ValueError("binding path must be repository-relative")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate_text).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("binding path escapes repository root") from exc
    return resolved


def _validate_section_seals(protocol: dict[str, Any], errors: list[str]) -> None:
    for section, expected_hash in EXPECTED_SECTION_SHA256.items():
        if section not in protocol:
            continue
        try:
            observed_hash = canonical_sha256(protocol[section])
        except (TypeError, ValueError) as exc:
            errors.append(f"cannot hash semantic section {section}: {exc}")
            continue
        if observed_hash != expected_hash:
            errors.append(
                f"sealed semantic section mismatch: {section} "
                f"(expected {expected_hash}, observed {observed_hash})"
            )


def _validate_external_bindings(
    protocol: dict[str, Any], root: Path, errors: list[str]
) -> None:
    bindings = _safe_object(protocol.get("immutable_bindings"))
    rows = _safe_list(bindings.get("external_files"))
    observed_pairs = [
        (row.get("role"), row.get("path"))
        for row in rows
        if isinstance(row, dict)
    ]
    if observed_pairs != list(EXPECTED_EXTERNAL_BINDINGS):
        errors.append("external binding roles/paths/order do not match the seal")
    roles = [pair[0] for pair in observed_pairs]
    if not all(isinstance(role, str) for role in roles) or len(roles) != len(
        set(roles)
    ):
        errors.append("duplicate external binding role")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"external binding {index} must be an object")
            continue
        digest = row.get("sha256")
        if not is_sha256(digest):
            errors.append(f"malformed SHA-256 at external binding {index}")
            continue
        try:
            path = _resolve_repo_path(root, row.get("path"))
        except ValueError as exc:
            errors.append(f"invalid external binding path {index}: {exc}")
            continue
        if not path.is_file():
            errors.append(f"bound external file is missing: {row.get('path')}")
            continue
        if file_sha256(path) != digest:
            errors.append(f"bound external file hash mismatch: {row.get('role')}")


def _validate_inline_bindings(protocol: dict[str, Any], errors: list[str]) -> None:
    bindings = _safe_object(protocol.get("immutable_bindings"))
    rows = _safe_list(bindings.get("inline_payloads"))
    observed_pairs = [
        (row.get("role"), row.get("json_pointer"))
        for row in rows
        if isinstance(row, dict)
    ]
    if observed_pairs != list(EXPECTED_INLINE_BINDINGS):
        errors.append("inline binding roles/pointers/order do not match the seal")
    roles = [pair[0] for pair in observed_pairs]
    if not all(isinstance(role, str) for role in roles) or len(roles) != len(
        set(roles)
    ):
        errors.append("duplicate inline binding role")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"inline binding {index} must be an object")
            continue
        digest = row.get("sha256")
        if not is_sha256(digest):
            errors.append(f"malformed SHA-256 at inline binding {index}")
            continue
        try:
            value = resolve_json_pointer(protocol, row.get("json_pointer"))
            observed = canonical_sha256(value)
        except (TypeError, ValueError) as exc:
            errors.append(f"invalid inline binding {index}: {exc}")
            continue
        if observed != digest:
            errors.append(f"inline payload hash mismatch: {row.get('role')}")


def _validate_identity_and_time(protocol: dict[str, Any], errors: list[str]) -> None:
    expected_identity = {
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "protocol_id": EXPECTED_PROTOCOL_ID,
        "version": EXPECTED_VERSION,
        "protocol_status": EXPECTED_STATUS,
    }
    for key, expected in expected_identity.items():
        if protocol.get(key) != expected or type(protocol.get(key)) is not type(expected):
            errors.append(f"identity mismatch at {key}: expected {expected!r}")

    registration = _safe_object(protocol.get("registration"))
    frozen_at = parse_utc_timestamp(registration.get("frozen_at_utc"))
    t0 = parse_utc_timestamp(registration.get("t0_utc"))
    if frozen_at is None:
        errors.append("registration.frozen_at_utc must be exact UTC ISO-8601 seconds")
    if t0 is None:
        errors.append("registration.t0_utc must be exact UTC ISO-8601 seconds")
    if frozen_at is not None and t0 is not None and t0 <= frozen_at:
        errors.append("registration.t0_utc must be after registration.frozen_at_utc")


def _validate_self_hash(protocol: dict[str, Any], errors: list[str]) -> None:
    bindings = _safe_object(protocol.get("immutable_bindings"))
    observed = bindings.get("protocol_payload_sha256")
    if not is_sha256(observed):
        errors.append("immutable_bindings.protocol_payload_sha256 is malformed")
        return
    try:
        computed = protocol_payload_sha256(protocol)
    except (TypeError, ValueError) as exc:
        errors.append(f"cannot compute protocol payload SHA-256: {exc}")
        return
    if observed != computed:
        errors.append(
            "protocol payload SHA-256 mismatch "
            f"(expected {observed}, computed {computed})"
        )


def _validate_boundaries(protocol: dict[str, Any], errors: list[str]) -> None:
    boundaries = _safe_object(protocol.get("boundaries"))
    if boundaries.get("mode") != "PAPER_ONLY":
        errors.append("forbidden mode: only PAPER_ONLY is permitted")
    if boundaries.get("asset_and_position_lane") != "LONG_FLAT_USD_SPOT":
        errors.append("forbidden asset or position lane")
    if boundaries.get("execution_capability") != "NONE":
        errors.append("validator/execution capability must remain NONE")
    if boundaries.get("public_unauthenticated_market_data_only") is not True:
        errors.append("public unauthenticated market data boundary was weakened")
    for key in FORBIDDEN_BOUNDARY_FLAGS:
        if boundaries.get(key) is not False:
            errors.append(f"forbidden capability enabled: {key}")

    registration = _safe_object(protocol.get("registration"))
    if registration.get("confirmatory_observations_before_t0_allowed") is not False:
        errors.append("confirmatory observations before T0 are forbidden")
    if registration.get("cross_version_result_bridging_allowed") is not False:
        errors.append("cross-version result bridging is forbidden")


def _validate_variants(protocol: dict[str, Any], errors: list[str]) -> None:
    family = _safe_object(protocol.get("candidate_family"))
    variants = _safe_list(family.get("variants"))
    ids = [row.get("id") for row in variants if isinstance(row, dict)]
    if len(variants) != 18 or family.get("attempt_count") != 18:
        errors.append("candidate family must contain exactly 18 attempted variants")
    if family.get("full_variant_count") != 12 or family.get("additional_test_count") != 6:
        errors.append("candidate family must contain exactly 12 full variants and 6 additional tests")
    if not all(isinstance(variant_id, str) for variant_id in ids) or len(ids) != len(
        set(ids)
    ):
        errors.append("duplicate candidate variant id")

    full_rows = [
        row for row in variants if isinstance(row, dict) and row.get("class") == "FULL_VARIANT"
    ]
    try:
        full_grid = {
            (
                row.get("entry_z_magnitude"),
                row.get("momentum_window_hours"),
                row.get("maximum_hold_hours"),
            )
            for row in full_rows
        }
    except TypeError:
        full_grid = set()
    if len(full_rows) != 12 or full_grid != EXPECTED_FULL_GRID:
        errors.append("full variant grid is not the exact registered 3x2x2 grid")

    additional_ids = [
        row.get("id")
        for row in variants
        if isinstance(row, dict) and row.get("class") != "FULL_VARIANT"
    ]
    if not all(isinstance(variant_id, str) for variant_id in additional_ids) or set(
        additional_ids
    ) != EXPECTED_ADDITIONAL_VARIANT_IDS:
        errors.append("the six registered ablations/placebo are not exact")
    if any(
        not isinstance(row, dict)
        or row.get("counts_from_first_run") is not True
        for row in variants
    ):
        errors.append("every variant must count from the first run")
    promotable = [row.get("id") for row in variants if isinstance(row, dict) and row.get("promotion_eligible") is True]
    if promotable != ["full_e2p0_m3_h12"]:
        errors.append("only the frozen 2.0/3h/12h primary may be promotion-eligible")


def _validate_counts_and_multiplicity(protocol: dict[str, Any], errors: list[str]) -> None:
    baselines = _safe_object(protocol.get("baselines"))
    baseline_rows = _safe_list(baselines.get("items"))
    baseline_ids = tuple(
        row.get("id") for row in baseline_rows if isinstance(row, dict)
    )
    if baselines.get("count") != 6 or len(baseline_rows) != 6:
        errors.append("baseline count must be exactly 6")
    if (
        baseline_ids != EXPECTED_BASELINE_IDS
        or not all(isinstance(baseline_id, str) for baseline_id in baseline_ids)
        or len(set(baseline_ids)) != 6
    ):
        errors.append("baseline registry is missing, reordered, extra, or duplicated")

    uncertainty = _safe_object(protocol.get("uncertainty_and_multiplicity"))
    fwer = _safe_object(uncertainty.get("fwer"))
    if not (
        fwer.get("variant_count") == 18
        and fwer.get("primary_baseline_count") == 2
        and fwer.get("contrast_count") == 36
        and fwer.get("preferred_method") == "ROMANO_WOLF_MAX_T"
        and fwer.get("fallback_method") == "HOLM_ACROSS_ALL_36"
        and fwer.get("alpha") == 0.05
    ):
        errors.append("Romano-Wolf/Holm 36-contrast FWER policy was weakened")
    if uncertainty.get("optional_stopping_allowed") is not False:
        errors.append("optional stopping is forbidden")
    if uncertainty.get("unregistered_subgroup_promotion_allowed") is not False:
        errors.append("unregistered subgroup promotion is forbidden")
    if uncertainty.get("planned_interim_count") != 1:
        errors.append("exactly one preregistered harm/futility interim is permitted")

    sample = _safe_object(protocol.get("sample_gates"))
    sample_rows = _safe_list(sample.get("gates"))
    sample_ids = tuple(row.get("id") for row in sample_rows if isinstance(row, dict))
    if sample.get("count") != 4 or len(sample_rows) != 4:
        errors.append("sample gate count must be exactly 4")
    if (
        sample_ids != EXPECTED_SAMPLE_GATE_IDS
        or not all(isinstance(gate_id, str) for gate_id in sample_ids)
        or len(set(sample_ids)) != 4
    ):
        errors.append("sample gates are missing, reordered, extra, or duplicated")
    if sample.get("thresholds_may_relax") is not False:
        errors.append("sample thresholds may not relax")

    promotion = _safe_object(protocol.get("promotion_policy"))
    promotion_rows = _safe_list(promotion.get("gates"))
    promotion_ids = tuple(
        row.get("id") for row in promotion_rows if isinstance(row, dict)
    )
    promotion_numbers = tuple(
        row.get("number") for row in promotion_rows if isinstance(row, dict)
    )
    if promotion.get("required_gate_count") != 11 or len(promotion_rows) != 11:
        errors.append("promotion gate count must be exactly 11")
    if (
        promotion_ids != EXPECTED_PROMOTION_GATE_IDS
        or not all(isinstance(gate_id, str) for gate_id in promotion_ids)
        or len(set(promotion_ids)) != 11
    ):
        errors.append("promotion gates are missing, reordered, extra, or duplicated")
    if promotion_numbers != tuple(range(1, 12)):
        errors.append("promotion gate numbers must be exactly 1 through 11")
    if promotion.get("all_gates_must_pass") is not True:
        errors.append("all 11 promotion gates must pass")


def _validate_claim_policy(protocol: dict[str, Any], errors: list[str]) -> None:
    claims = _safe_object(protocol.get("claim_policy"))
    if claims.get("declared_result_label") != "NO_PROSPECTIVE_RESULT":
        errors.append("a preregistration cannot declare a prospective result")
    if claims.get("allowed_success_label") != EXPECTED_SUCCESS_LABEL:
        errors.append("allowed success label exceeds or differs from the sealed claim")
    if claims.get("maximum_claim_label") != EXPECTED_SUCCESS_LABEL:
        errors.append("claim ceiling must be PROSPECTIVE_PAPER_EDGE_SUPPORTED")
    if claims.get("success_requires_all_11_promotion_gates") is not True:
        errors.append("success must require all 11 promotion gates")
    for key in (
        "live_alpha_claim_allowed",
        "institutional_capacity_claim_allowed",
        "large_fund_claim_allowed",
        "universal_superiority_claim_allowed",
        "profitable_live_claim_allowed",
    ):
        if claims.get(key) is not False:
            errors.append(f"claim beyond paper edge enabled: {key}")


def validate_protocol(protocol: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    """Return all fail-closed validation errors for a protocol object."""

    errors: list[str] = []
    if not isinstance(protocol, dict):
        return ["protocol must be a JSON object"]

    _walk_structure(protocol, "$", errors)
    _validate_identity_and_time(protocol, errors)
    _validate_boundaries(protocol, errors)
    _validate_variants(protocol, errors)
    _validate_counts_and_multiplicity(protocol, errors)
    _validate_claim_policy(protocol, errors)
    _validate_inline_bindings(protocol, errors)
    _validate_external_bindings(protocol, root, errors)
    _validate_self_hash(protocol, errors)
    _validate_section_seals(protocol, errors)
    return errors


def validation_report(protocol_path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    try:
        protocol = read_json(protocol_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "protocol_path": str(protocol_path),
            "valid": False,
            "error_count": 1,
            "errors": [f"protocol load failed: {exc}"],
            "validation_only": True,
            "network_or_execution_performed": False,
        }

    errors = validate_protocol(protocol, root=ROOT)
    bindings = _safe_object(protocol.get("immutable_bindings"))
    report: dict[str, Any] = {
        "protocol_path": str(protocol_path),
        "protocol_id": protocol.get("protocol_id"),
        "mode": _safe_object(protocol.get("boundaries")).get("mode"),
        "declared_result_label": _safe_object(protocol.get("claim_policy")).get(
            "declared_result_label"
        ),
        "maximum_claim_label": _safe_object(protocol.get("claim_policy")).get(
            "maximum_claim_label"
        ),
        "registered_variant_count": len(
            _safe_list(_safe_object(protocol.get("candidate_family")).get("variants"))
        ),
        "promotion_gate_count": len(
            _safe_list(_safe_object(protocol.get("promotion_policy")).get("gates"))
        ),
        "protocol_payload_sha256": bindings.get("protocol_payload_sha256"),
        "valid": not errors,
        "error_count": len(errors),
        "errors": errors,
        "validation_only": True,
        "network_or_execution_performed": False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the sealed CS dislocation paper-only preregistration."
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=DEFAULT_PROTOCOL,
        help="Protocol JSON path (default: the sealed V1 config).",
    )
    args = parser.parse_args()
    report = validation_report(args.protocol)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
