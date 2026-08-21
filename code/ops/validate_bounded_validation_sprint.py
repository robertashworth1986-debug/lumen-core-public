#!/usr/bin/env python3
"""Fail-closed validation for the proposed LumenCore Bounded Validation Sprint offer."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA = "lumencore_bounded_validation_sprint_v1"
ALLOWED_STATUSES = {"proposed_founder_review", "approved_for_use", "retired"}
ALLOWED_DECISIONS = {"promote", "rerun", "external_review", "hold", "reject"}
ALLOWED_RIGHTS = {"public", "synthetic", "buyer_authorized"}
REQUIRED_APPROVAL_KEYS = {
    "founder_approved_for_external_use",
    "legal_review_complete",
    "pricing_tested_with_buyers",
    "first_paid_scope_signed",
}
REQUIRED_SCOPE_KEYS = {
    "authorized_sources_max",
    "baselines_max",
    "primary_metrics_max",
    "held_out_windows_max",
    "reviewer_reruns_included",
    "briefings_included",
}
REQUIRED_EXCLUSIONS = {
    "classified information",
    "controlled unclassified information",
    "protected health information",
    "payment card data",
    "export-controlled technical data",
    "production credentials",
    "live autonomous physical-control access",
}
REQUIRED_PRE_REGISTERED_FIELDS = {
    "source and rights owner",
    "incumbent baseline",
    "primary metric",
    "acceptance threshold",
    "held-out window or frozen seeds",
    "failure and incomplete-run rules",
    "allowed public claims",
    "decision owner",
    "execution boundary and human approval owner",
    "economic denominator, eligibility, realization, cost, and non-overlap group",
}
REQUIRED_DELIVERABLES = {
    "source and rights label",
    "frozen baseline and metric contract",
    "baseline-versus-candidate replay or benchmark",
    "failure and negative-result register",
    "SHA-256 input/output manifest",
    "offline verification instructions",
    "buyer-readable Proof Capsule",
    "one bounded go/no-go decision briefing",
    "read-only shadow comparison receipt",
    "non-overlapping economic conversion ledger",
}
REQUIRED_EXECUTION_BOUNDARY_KEYS = {
    "mode",
    "production_write_access",
    "actuation_allowed",
    "production_credentials_allowed",
    "recommendations_require_human_approval",
    "matched_conditions_required",
    "incumbent_fallback_required",
    "comparison_arms",
}
REQUIRED_COMPARISON_ARMS = {"incumbent", "candidate", "alternative_optional"}
REQUIRED_ECONOMIC_CONVERSION_KEYS = {
    "status",
    "required_inputs",
    "eligible_share_min",
    "eligible_share_max",
    "realization_factor_min",
    "realization_factor_max",
    "implementation_and_run_costs_required",
    "non_overlap_ledger_required",
    "public_value_claims_allowed",
}
REQUIRED_ECONOMIC_INPUTS = {
    "buyer-owned addressable cost denominator",
    "denominator currency, unit, and time window",
    "eligible share",
    "measured technical delta",
    "realization factor",
    "implementation and run costs",
    "non-overlap group",
}
REQUIRED_DOC_PHRASES = {
    "offer": (
        "one controlled, inspectable decision",
        "a favorable result is not promised",
        "classified information",
        "each retain their pre-existing",
        "evidence before claims",
        "read-only shadow",
        "non-overlap ledger",
    ),
    "sow": (
        "a favorable decision is not promised",
        "selected before scoring",
        "negative-result register",
        "no ownership transfer",
        "do not sign this template",
        "read-only shadow",
        "buyer-owned denominator",
    ),
}
UNSAFE_CLAIM_PHRASES = (
    "guaranteed return on investment",
    "guaranteed savings",
    "field validation is established",
    "agency endorsement is confirmed",
    "certification is complete",
    "customer deployment is confirmed",
    "award is guaranteed",
    "production authorization is granted",
)
NEGATION_MARKERS = (
    "no ",
    "not ",
    "does not ",
    "do not ",
    "did not ",
    "is not ",
    "are not ",
    "cannot ",
    "can't ",
    "without ",
    "never ",
    "neither ",
)
TIER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
SENTENCE_BOUNDARY_RE = re.compile(r"[.!?;\n]")


class OfferValidationError(ValueError):
    """Raised when the proposed offer fails a commercial or claim-safety gate."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OfferValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, *, max_bytes: int = 1_048_576) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise OfferValidationError(f"cannot read {path}: {exc}") from exc
    if len(raw) > max_bytes:
        raise OfferValidationError(f"offer file exceeds {max_bytes} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OfferValidationError("offer file must be UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise OfferValidationError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise OfferValidationError("offer root must be an object")
    return value


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise OfferValidationError(f"{key} must be an object")
    return value


def _list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise OfferValidationError(f"{key} must be an array")
    return value


def _string(parent: dict[str, Any], key: str, *, context: str = "offer") -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OfferValidationError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _integer(
    parent: dict[str, Any],
    key: str,
    *,
    context: str,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise OfferValidationError(f"{context}.{key} must be an integer")
    if value < minimum:
        raise OfferValidationError(f"{context}.{key} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise OfferValidationError(f"{context}.{key} must not exceed {maximum}")
    return value


def _number(
    parent: dict[str, Any],
    key: str,
    *,
    context: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OfferValidationError(f"{context}.{key} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise OfferValidationError(f"{context}.{key} must be finite")
    if minimum is not None and number < minimum:
        raise OfferValidationError(f"{context}.{key} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise OfferValidationError(f"{context}.{key} must not exceed {maximum}")
    return number


def _normalized_string_set(values: Iterable[Any], *, context: str) -> set[str]:
    result: set[str] = set()
    seen: set[str] = set()
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise OfferValidationError(f"{context}[{index}] must be a non-empty string")
        normalized = value.strip()
        key = normalized.casefold()
        if key in seen:
            raise OfferValidationError(f"{context} contains duplicate entry: {normalized}")
        seen.add(key)
        result.add(normalized)
    return result


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _unsafe_positive_hits(text: str) -> set[str]:
    """Detect positive unsafe assertions while allowing explicit negated boundaries."""
    lowered = text.casefold()
    hits: set[str] = set()
    for phrase in UNSAFE_CLAIM_PHRASES:
        start = 0
        while True:
            index = lowered.find(phrase, start)
            if index < 0:
                break
            prefix = lowered[:index]
            boundaries = list(SENTENCE_BOUNDARY_RE.finditer(prefix))
            sentence_start = boundaries[-1].end() if boundaries else 0
            local_prefix = prefix[sentence_start:index][-120:]
            if not any(marker in local_prefix for marker in NEGATION_MARKERS):
                hits.add(phrase)
            start = index + len(phrase)
    return hits


def _validate_no_unsafe_positive_claims(value: Any, *, context: str) -> None:
    hits: set[str] = set()
    for text in _iter_strings(value):
        hits.update(_unsafe_positive_hits(text))
    if hits:
        raise OfferValidationError(
            f"{context}: unsafe positive assertion(s): " + ", ".join(sorted(hits))
        )


def validate_offer(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != SCHEMA:
        raise OfferValidationError(f"schema must be {SCHEMA}")
    if payload.get("version") != "1.0.0":
        raise OfferValidationError("version must be 1.0.0")

    status = _string(payload, "status")
    if status not in ALLOWED_STATUSES:
        raise OfferValidationError(f"unsupported status: {status}")
    if payload.get("currency") != "USD":
        raise OfferValidationError("currency must be USD")
    _string(payload, "commercial_position")

    offer = _mapping(payload, "offer")
    if _integer(
        offer,
        "duration_calendar_days_max",
        context="offer",
        minimum=1,
        maximum=30,
    ) != 30:
        raise OfferValidationError(
            "the canonical sprint duration must remain 30 calendar days"
        )

    decisions = {
        item.strip()
        for item in _string(offer, "buyer_decision", context="offer").split("|")
    }
    if decisions != ALLOWED_DECISIONS:
        raise OfferValidationError(
            "offer.buyer_decision must enumerate the five bounded decisions"
        )

    rights = _normalized_string_set(
        _list(offer, "accepted_source_rights"),
        context="offer.accepted_source_rights",
    )
    if rights != ALLOWED_RIGHTS:
        raise OfferValidationError(
            "accepted_source_rights must be public, synthetic, and buyer_authorized"
        )

    execution_boundary = _mapping(offer, "execution_boundary")
    if set(execution_boundary) != REQUIRED_EXECUTION_BOUNDARY_KEYS:
        missing = sorted(REQUIRED_EXECUTION_BOUNDARY_KEYS - set(execution_boundary))
        extra = sorted(set(execution_boundary) - REQUIRED_EXECUTION_BOUNDARY_KEYS)
        raise OfferValidationError(
            "offer.execution_boundary mismatch; "
            f"missing={missing}, extra={extra}"
        )
    if execution_boundary.get("mode") != "read_only_shadow":
        raise OfferValidationError(
            "offer.execution_boundary.mode must be read_only_shadow"
        )
    for key in (
        "production_write_access",
        "actuation_allowed",
        "production_credentials_allowed",
    ):
        if execution_boundary.get(key) is not False:
            raise OfferValidationError(
                f"offer.execution_boundary.{key} must be false"
            )
    for key in (
        "recommendations_require_human_approval",
        "matched_conditions_required",
        "incumbent_fallback_required",
    ):
        if execution_boundary.get(key) is not True:
            raise OfferValidationError(
                f"offer.execution_boundary.{key} must be true"
            )
    comparison_arms = _normalized_string_set(
        _list(execution_boundary, "comparison_arms"),
        context="offer.execution_boundary.comparison_arms",
    )
    if comparison_arms != REQUIRED_COMPARISON_ARMS:
        raise OfferValidationError(
            "comparison_arms must include incumbent, candidate, and alternative_optional"
        )

    economic_gate = _mapping(offer, "economic_conversion_gate")
    if set(economic_gate) != REQUIRED_ECONOMIC_CONVERSION_KEYS:
        missing = sorted(REQUIRED_ECONOMIC_CONVERSION_KEYS - set(economic_gate))
        extra = sorted(set(economic_gate) - REQUIRED_ECONOMIC_CONVERSION_KEYS)
        raise OfferValidationError(
            "offer.economic_conversion_gate mismatch; "
            f"missing={missing}, extra={extra}"
        )
    if economic_gate.get("status") != "disabled_until_complete":
        raise OfferValidationError(
            "economic conversion must remain disabled until buyer-owned inputs are complete"
        )
    economic_inputs = _normalized_string_set(
        _list(economic_gate, "required_inputs"),
        context="offer.economic_conversion_gate.required_inputs",
    )
    if economic_inputs != REQUIRED_ECONOMIC_INPUTS:
        missing = sorted(REQUIRED_ECONOMIC_INPUTS - economic_inputs)
        extra = sorted(economic_inputs - REQUIRED_ECONOMIC_INPUTS)
        raise OfferValidationError(
            "economic conversion inputs mismatch; "
            f"missing={missing}, extra={extra}"
        )
    bounds = {
        "eligible_share_min": _number(
            economic_gate,
            "eligible_share_min",
            context="offer.economic_conversion_gate",
            minimum=0.0,
            maximum=1.0,
        ),
        "eligible_share_max": _number(
            economic_gate,
            "eligible_share_max",
            context="offer.economic_conversion_gate",
            minimum=0.0,
            maximum=1.0,
        ),
        "realization_factor_min": _number(
            economic_gate,
            "realization_factor_min",
            context="offer.economic_conversion_gate",
            minimum=0.0,
            maximum=1.0,
        ),
        "realization_factor_max": _number(
            economic_gate,
            "realization_factor_max",
            context="offer.economic_conversion_gate",
            minimum=0.0,
            maximum=1.0,
        ),
    }
    if bounds != {
        "eligible_share_min": 0.0,
        "eligible_share_max": 1.0,
        "realization_factor_min": 0.0,
        "realization_factor_max": 1.0,
    }:
        raise OfferValidationError(
            "economic conversion bounds must remain the closed interval [0, 1]"
        )
    for key in (
        "implementation_and_run_costs_required",
        "non_overlap_ledger_required",
    ):
        if economic_gate.get(key) is not True:
            raise OfferValidationError(
                f"offer.economic_conversion_gate.{key} must be true"
            )
    if economic_gate.get("public_value_claims_allowed") is not False:
        raise OfferValidationError(
            "public value claims must remain disabled by the offer registry"
        )

    exclusions = _normalized_string_set(
        _list(offer, "excluded_without_separate_written_controls"),
        context="offer.excluded_without_separate_written_controls",
    )
    missing_exclusions = sorted(REQUIRED_EXCLUSIONS - exclusions)
    if missing_exclusions:
        raise OfferValidationError(
            "missing required exclusion(s): " + ", ".join(missing_exclusions)
        )

    pre_registered = _normalized_string_set(
        _list(offer, "pre_registered_fields"),
        context="offer.pre_registered_fields",
    )
    missing_fields = sorted(REQUIRED_PRE_REGISTERED_FIELDS - pre_registered)
    if missing_fields:
        raise OfferValidationError(
            "missing pre-registered field(s): " + ", ".join(missing_fields)
        )

    deliverables = _normalized_string_set(
        _list(offer, "required_deliverables"),
        context="offer.required_deliverables",
    )
    missing_deliverables = sorted(REQUIRED_DELIVERABLES - deliverables)
    if missing_deliverables:
        raise OfferValidationError(
            "missing required deliverable(s): " + ", ".join(missing_deliverables)
        )

    boundaries = _normalized_string_set(
        _list(offer, "claim_boundary"),
        context="offer.claim_boundary",
    )
    boundary_text = " ".join(boundaries).casefold()
    for concept in ("no guaranteed", "not field validation", "cannot strengthen"):
        if concept not in boundary_text:
            raise OfferValidationError(f"claim boundary missing concept: {concept}")

    tiers = _list(payload, "tiers")
    if len(tiers) != 3:
        raise OfferValidationError("exactly three proposed launch tiers are required")

    tier_ids: set[str] = set()
    prices: list[int] = []
    for index, raw_tier in enumerate(tiers):
        if not isinstance(raw_tier, dict):
            raise OfferValidationError(f"tiers[{index}] must be an object")
        context = f"tiers[{index}]"
        tier_id = _string(raw_tier, "tier_id", context=context)
        if not TIER_ID_RE.fullmatch(tier_id):
            raise OfferValidationError(f"{context}.tier_id is not canonical")
        if tier_id in tier_ids:
            raise OfferValidationError(f"duplicate tier_id: {tier_id}")
        tier_ids.add(tier_id)
        _string(raw_tier, "name", context=context)
        price = _integer(
            raw_tier,
            "proposed_price_usd",
            context=context,
            minimum=1_000,
            maximum=1_000_000,
        )
        prices.append(price)
        _integer(
            raw_tier,
            "deposit_percent",
            context=context,
            minimum=1,
            maximum=100,
        )
        _integer(
            raw_tier,
            "duration_calendar_days_max",
            context=context,
            minimum=1,
            maximum=30,
        )
        _string(raw_tier, "best_for", context=context)
        limits = _mapping(raw_tier, "scope_limits")
        if set(limits) != REQUIRED_SCOPE_KEYS:
            missing = sorted(REQUIRED_SCOPE_KEYS - set(limits))
            extra = sorted(set(limits) - REQUIRED_SCOPE_KEYS)
            raise OfferValidationError(
                f"{context}.scope_limits mismatch; missing={missing}, extra={extra}"
            )
        for key in REQUIRED_SCOPE_KEYS:
            _integer(
                limits,
                key,
                context=f"{context}.scope_limits",
                minimum=0,
                maximum=100,
            )
        if limits["primary_metrics_max"] != 1:
            raise OfferValidationError(f"{context} must keep one primary metric")
        if limits["authorized_sources_max"] < 1 or limits["baselines_max"] < 1:
            raise OfferValidationError(
                f"{context} requires at least one source and one baseline"
            )

    if prices != sorted(prices) or len(set(prices)) != len(prices):
        raise OfferValidationError(
            "tier prices must be unique and strictly increasing"
        )

    payment = _mapping(payload, "payment")
    for key in ("commercial_default", "government_boundary", "out_of_scope_work"):
        _string(payment, key, context="payment")

    ip_boundary = _mapping(payload, "ip_boundary")
    for key in ("background_ip", "buyer_data", "sprint_outputs", "publicity"):
        _string(ip_boundary, key, context="ip_boundary")

    approval = _mapping(payload, "approval")
    if set(approval) != REQUIRED_APPROVAL_KEYS:
        raise OfferValidationError(
            "approval keys do not match the canonical approval gate"
        )
    for key, value in approval.items():
        if not isinstance(value, bool):
            raise OfferValidationError(f"approval.{key} must be boolean")
    if (
        status == "proposed_founder_review"
        and approval["founder_approved_for_external_use"]
    ):
        raise OfferValidationError(
            "proposed offer cannot claim founder approval for external use"
        )
    if status == "approved_for_use" and not approval[
        "founder_approved_for_external_use"
    ]:
        raise OfferValidationError("approved offer requires founder approval")

    _validate_no_unsafe_positive_claims(payload, context="offer")
    return {
        "valid": True,
        "schema": SCHEMA,
        "version": payload["version"],
        "status": status,
        "tier_count": len(tiers),
        "tier_ids": sorted(tier_ids),
        "proposed_prices_usd": prices,
        "duration_calendar_days_max": offer["duration_calendar_days_max"],
        "founder_approved_for_external_use": approval[
            "founder_approved_for_external_use"
        ],
        "legal_review_complete": approval["legal_review_complete"],
    }


def validate_documents(root: Path) -> dict[str, Any]:
    paths = {
        "offer": root / "docs" / "LUMENCORE_BOUNDED_VALIDATION_SPRINT_OFFER.md",
        "sow": root
        / "docs"
        / "LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md",
    }
    result: dict[str, Any] = {}
    for label, path in paths.items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OfferValidationError(f"cannot read {path}: {exc}") from exc
        lowered = text.casefold()
        for phrase in REQUIRED_DOC_PHRASES[label]:
            if phrase.casefold() not in lowered:
                raise OfferValidationError(
                    f"{path}: required phrase missing: {phrase}"
                )
        hits = _unsafe_positive_hits(text)
        if hits:
            raise OfferValidationError(
                f"{path}: unsafe positive assertion(s): "
                + ", ".join(sorted(hits))
            )
        result[label] = {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
        }
    return result


def validate_repository(root: Path) -> dict[str, Any]:
    offer_path = root / "config" / "bounded_validation_sprint_v1.json"
    payload = load_json(offer_path)
    result = validate_offer(payload)
    result["documents"] = validate_documents(root)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        result = validate_repository(args.root.resolve())
    except OfferValidationError as exc:
        print(
            json.dumps({"valid": False, "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
