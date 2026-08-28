#!/usr/bin/env python3
"""Fail closed when public LumenCore surfaces disagree about the paid offer."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CANONICAL_OFFER_ID = "buyer-owned-baseline-validation-sprint"
CANONICAL_OFFER_NAME = "LumenCore 30-Day Bounded Validation Sprint"
CANONICAL_PUBLIC_URL = "https://lumen-core.ai/proof_to_pilot.html"
CANONICAL_TIERS = [
    {
        "tier_id": "launch_replay",
        "name": "Launch Replay",
        "proposed_price_usd": 7500,
        "price_basis": "fixed",
        "deposit_percent": 50,
    },
    {
        "tier_id": "standard_sprint",
        "name": "Standard Sprint",
        "proposed_price_usd": 15000,
        "price_basis": "fixed",
        "deposit_percent": 50,
    },
    {
        "tier_id": "institutional_sprint",
        "name": "Institutional Sprint",
        "proposed_price_usd": 25000,
        "price_basis": "starting_at",
        "deposit_percent": 50,
    },
]
MAX_JSON_BYTES = 1_000_000


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def load_json_strict(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"{path} exceeds {MAX_JSON_BYTES} bytes")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path} root must be an object")
    return value


def normalized_tiers(sprint: dict[str, Any]) -> list[dict[str, Any]]:
    tiers = sprint.get("tiers")
    if not isinstance(tiers, list):
        raise ValueError("bounded sprint tiers must be a list")
    normalized: list[dict[str, Any]] = []
    for tier in tiers:
        if not isinstance(tier, dict):
            raise ValueError("every bounded sprint tier must be an object")
        normalized.append(
            {
                "tier_id": tier.get("tier_id"),
                "name": tier.get("name"),
                "proposed_price_usd": tier.get("proposed_price_usd"),
                "price_basis": tier.get("price_basis", "fixed"),
                "deposit_percent": tier.get("deposit_percent"),
            }
        )
    return normalized


def require_contains(text: str, needles: tuple[str, ...], label: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise ValueError(f"{label} is missing canonical offer text: {missing}")


def verify_contracts(
    strategic: dict[str, Any],
    sprint: dict[str, Any],
    docket: dict[str, Any],
    surfaces: dict[str, str],
) -> dict[str, Any]:
    primary = strategic.get("primary_offer")
    if not isinstance(primary, dict) or primary.get("id") != CANONICAL_OFFER_ID:
        raise ValueError("strategic packet primary offer id mismatch")
    if strategic.get("public_contact_path") != CANONICAL_PUBLIC_URL:
        raise ValueError("strategic packet public contact path mismatch")

    offer = sprint.get("offer")
    if not isinstance(offer, dict) or offer.get("name") != CANONICAL_OFFER_NAME:
        raise ValueError("bounded sprint offer name mismatch")
    if offer.get("duration_calendar_days_max") != 30:
        raise ValueError("bounded sprint duration mismatch")
    if normalized_tiers(sprint) != CANONICAL_TIERS:
        raise ValueError("bounded sprint tier contract mismatch")
    approval = sprint.get("approval")
    if not isinstance(approval, dict):
        raise ValueError("bounded sprint approval block missing")
    if approval.get("pricing_tested_with_buyers") is not False:
        raise ValueError("pricing must remain explicitly untested with buyers")
    if approval.get("first_paid_scope_signed") is not False:
        raise ValueError("first paid scope must remain explicitly unsigned")

    if docket.get("schema") != "lumencore.public_reviewer_docket.v2":
        raise ValueError("reviewer docket schema mismatch")
    paid = docket.get("primary_paid_offer")
    if not isinstance(paid, dict):
        raise ValueError("reviewer docket primary paid offer missing")
    if paid.get("id") != CANONICAL_OFFER_ID:
        raise ValueError("reviewer docket primary offer id mismatch")
    if paid.get("name") != CANONICAL_OFFER_NAME:
        raise ValueError("reviewer docket offer name mismatch")
    if paid.get("public_url") != CANONICAL_PUBLIC_URL:
        raise ValueError("reviewer docket public URL mismatch")
    if paid.get("duration_calendar_days_max") != 30:
        raise ValueError("reviewer docket duration mismatch")
    if paid.get("commercial_state") != "offer_defined_no_signed_scope_no_payment":
        raise ValueError("reviewer docket commercial state mismatch")
    if paid.get("pricing_status") != "founder_approved_hypothesis_not_buyer_tested":
        raise ValueError("reviewer docket pricing status mismatch")
    if paid.get("tiers") != CANONICAL_TIERS:
        raise ValueError("reviewer docket tier contract mismatch")

    require_contains(
        surfaces["readme"],
        (
            "sole primary paid entry point",
            "Buyer-Owned Baseline Validation Sprint",
            "$7,500",
            "$15,000",
            "$25,000",
            "not buyer-tested",
        ),
        "README",
    )
    require_contains(
        surfaces["reviewer_start"],
        (
            "LumenCore is the platform. ProofLock is its evidence and claim-governance layer.",
            "Frozen Delta",
            "Buyer-Owned Baseline Validation Sprint",
        ),
        "reviewer start",
    )
    require_contains(
        surfaces["home"],
        (
            "Buyer-Owned Baseline Validation Sprint",
            "$7,500",
            "Pricing is not buyer-tested",
            'href="/proof_to_pilot.html"',
        ),
        "public home",
    )
    if "ProofLock Opportunity Sprint" in surfaces["home"]:
        raise ValueError("public home still promotes the superseded primary offer")
    require_contains(
        surfaces["proof_to_pilot"],
        (
            "One candidate. One accepted baseline. One decision you can defend.",
            "Frozen Delta is the method inside this one bounded offer",
            "$7,500",
            "$15,000",
            "From $25,000",
            "Pricing is an offer hypothesis, not booked revenue",
        ),
        "proof-to-pilot page",
    )
    require_contains(
        surfaces["opportunity_sprint"],
        (
            "Secondary funding-workflow variant",
            "not the primary public offer",
            "No active standalone public price",
            'href="/proof_to_pilot.html"',
        ),
        "secondary funding-workflow page",
    )

    return {
        "valid": True,
        "primary_offer_id": CANONICAL_OFFER_ID,
        "primary_public_url": CANONICAL_PUBLIC_URL,
        "tier_prices_usd": [tier["proposed_price_usd"] for tier in CANONICAL_TIERS],
        "pricing_tested_with_buyers": False,
        "signed_scope_claimed": False,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_repository(root: Path) -> dict[str, Any]:
    json_paths = {
        "strategic": root / "config" / "strategic_transaction_packet_v2.json",
        "sprint": root / "config" / "bounded_validation_sprint_v1.json",
        "docket": root / "dashboard" / "reviewer_docket.json",
    }
    surface_paths = {
        "readme": root / "README.md",
        "reviewer_start": root / "docs" / "REVIEWER_START_HERE.md",
        "home": root / "dashboard" / "operator_home.html",
        "proof_to_pilot": root / "dashboard" / "proof_to_pilot.html",
        "opportunity_sprint": root / "dashboard" / "opportunity_sprint.html",
    }
    result = verify_contracts(
        load_json_strict(json_paths["strategic"]),
        load_json_strict(json_paths["sprint"]),
        load_json_strict(json_paths["docket"]),
        {name: path.read_text(encoding="utf-8") for name, path in surface_paths.items()},
    )
    all_paths = {**json_paths, **surface_paths}
    result["artifact_sha256"] = {
        name: sha256(path) for name, path in sorted(all_paths.items())
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = verify_repository(args.root.resolve())
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        result = {"valid": False, "error": str(exc)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
