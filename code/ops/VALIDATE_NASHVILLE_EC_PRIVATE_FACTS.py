from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PRIVATE_REPO_DIR = (
    ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026" / "private"
)
SCHEMA = "lumencore.nashville_ec_private_founder_facts.v1"
OUTPUT_SCHEMA = "lumencore.nashville_ec_private_portal_fill_map.v1"
BUSINESS_AGE_OPTIONS = {
    "Not yet started",
    "Less than 6 months",
    "6 to 12 months",
    "1 to 3 years",
    "3+ years",
}
HOURS_ALIASES = {
    "Less than 10": "Less than 10",
    "10-20": "10\u201320",
    "10\u201320": "10\u201320",
    "20-30": "20\u201330",
    "20\u201330": "20\u201330",
    "30+": "30+",
}
CONVERSATION_OPTIONS = {"0", "1 to 10", "11 to 25", "26 to 50", "50+"}
FINANCIAL_KEYS = (
    "previous_year_revenue_usd",
    "trailing_12_month_revenue_usd",
    "grant_funds_received_usd",
    "investor_capital_received_usd",
)
EXPECTED_KEYS = {
    "schema",
    "first_time_founder",
    "business_age",
    "full_time_on_lumencore",
    "weekly_hours_bracket",
    "conversation_bracket",
    "zero_financials_confirmed",
    "financial_amounts_usd",
    "founder_cash_invested_usd",
    "business_debt_usd",
}
MAX_USD = Decimal("1000000000000")


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be true or false")
    return value


def require_option(value: Any, field: str, options: set[str]) -> str:
    if not isinstance(value, str) or value not in options:
        raise ValueError(f"{field} must be one of: {sorted(options)}")
    return value


def parse_usd(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be a nonnegative USD amount")
    if isinstance(value, (int, float, Decimal)):
        candidate = str(value)
    elif isinstance(value, str):
        candidate = value.strip().replace("$", "").replace(",", "")
    else:
        raise ValueError(f"{field} must be a nonnegative USD amount")
    try:
        amount = Decimal(candidate)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a valid USD amount") from exc
    if not amount.is_finite() or amount < 0 or amount > MAX_USD:
        raise ValueError(f"{field} must be between $0 and ${MAX_USD}")
    if amount.as_tuple().exponent < -2:
        raise ValueError(f"{field} may have at most two decimal places")
    return amount


def format_usd(amount: Decimal) -> str:
    rendered = f"{amount:.2f}"
    if rendered.endswith(".00"):
        rendered = rendered[:-3]
    return f"${rendered}"


def output_path_allowed(path: Path) -> bool:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return True
    try:
        resolved.relative_to(PRIVATE_REPO_DIR.resolve())
    except ValueError:
        return False
    return True


def validate_private_facts(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Private founder facts must be a JSON object")
    unknown = set(payload) - EXPECTED_KEYS
    missing = EXPECTED_KEYS - set(payload)
    if unknown:
        raise ValueError(f"Unknown private founder fact keys: {sorted(unknown)}")
    if missing:
        raise ValueError(f"Missing private founder fact keys: {sorted(missing)}")
    if payload["schema"] != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")

    first_time = require_bool(payload["first_time_founder"], "first_time_founder")
    business_age = require_option(
        payload["business_age"], "business_age", BUSINESS_AGE_OPTIONS
    )
    full_time = require_bool(
        payload["full_time_on_lumencore"], "full_time_on_lumencore"
    )
    hours_input = payload["weekly_hours_bracket"]
    if not isinstance(hours_input, str) or hours_input not in HOURS_ALIASES:
        raise ValueError(
            "weekly_hours_bracket must be one of: Less than 10, 10-20, 20-30, 30+"
        )
    hours = HOURS_ALIASES[hours_input]
    conversations = require_option(
        payload["conversation_bracket"],
        "conversation_bracket",
        CONVERSATION_OPTIONS,
    )
    zero_confirmed = require_bool(
        payload["zero_financials_confirmed"], "zero_financials_confirmed"
    )

    supplied_financials = payload["financial_amounts_usd"]
    if supplied_financials is not None and not isinstance(supplied_financials, dict):
        raise ValueError("financial_amounts_usd must be null or an object")
    financials: dict[str, Decimal]
    if zero_confirmed:
        if supplied_financials is not None:
            unknown_financials = set(supplied_financials) - set(FINANCIAL_KEYS)
            if unknown_financials:
                raise ValueError(
                    f"Unknown financial amount keys: {sorted(unknown_financials)}"
                )
            parsed_supplied = {
                key: parse_usd(value, key)
                for key, value in supplied_financials.items()
            }
            if any(amount != 0 for amount in parsed_supplied.values()):
                raise ValueError(
                    "zero_financials_confirmed cannot be true when a supplied financial amount is nonzero"
                )
        financials = {key: Decimal("0") for key in FINANCIAL_KEYS}
    else:
        if supplied_financials is None:
            raise ValueError(
                "financial_amounts_usd is required when zero_financials_confirmed is false"
            )
        unknown_financials = set(supplied_financials) - set(FINANCIAL_KEYS)
        missing_financials = set(FINANCIAL_KEYS) - set(supplied_financials)
        if unknown_financials or missing_financials:
            raise ValueError(
                "financial_amounts_usd must contain exactly: "
                f"{list(FINANCIAL_KEYS)}"
            )
        financials = {
            key: parse_usd(supplied_financials[key], key)
            for key in FINANCIAL_KEYS
        }

    founder_cash = parse_usd(
        payload["founder_cash_invested_usd"], "founder_cash_invested_usd"
    )
    business_debt = parse_usd(payload["business_debt_usd"], "business_debt_usd")
    answers = [
        {"question_id": 38, "value": "Yes" if first_time else "No"},
        {"question_id": 31, "value": business_age},
        {"question_id": 28, "value": "Yes" if full_time else "No"},
        {"question_id": 29, "value": hours},
        {"question_id": 84, "value": conversations},
        {"question_id": 66, "value": format_usd(financials["previous_year_revenue_usd"])},
        {
            "question_id": 36,
            "value": format_usd(financials["trailing_12_month_revenue_usd"]),
        },
        {"question_id": 63, "value": format_usd(financials["grant_funds_received_usd"])},
        {
            "question_id": 64,
            "value": format_usd(financials["investor_capital_received_usd"]),
        },
        {"question_id": 62, "value": format_usd(founder_cash)},
        {"question_id": 65, "value": format_usd(business_debt)},
    ]
    result: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "generated_utc": now_utc(),
        "status": "VALIDATED_PRIVATE_PORTAL_FILL_MAP",
        "private_portal_only": True,
        "public_repo_publish_allowed": False,
        "question_answer_count": len(answers),
        "question_answers": answers,
        "final_action_gate": {
            "private_facts_validated": True,
            "live_portal_preview_reviewed": False,
            "fee_and_terms_reviewed": False,
            "final_submission_authorized_at_action_time": False,
        },
        "claim_boundary": (
            "Validation proves only that founder-provided values match the captured portal schemas "
            "and currency rules. It does not prove the facts independently, submit the application, "
            "authorize fees or terms, or establish acceptance, funding, validation, or an award."
        ),
    }
    result["private_fill_map_sha256"] = stable_hash(result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate private Nashville EC founder facts and emit a portal-only fill map."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = (
        args.output.resolve()
        if args.output
        else input_path.with_name("nashville_ec_portal_fill_map.private.json")
    )
    if not output_path_allowed(output_path):
        raise SystemExit(
            "Refusing to write private founder facts into a tracked repository location. "
            f"Use {PRIVATE_REPO_DIR} or a path outside the repository."
        )
    source = json.loads(input_path.read_text(encoding="utf-8-sig"))
    result = validate_private_facts(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "question_answer_count": result["question_answer_count"],
                "private_portal_only": result["private_portal_only"],
                "public_repo_publish_allowed": result["public_repo_publish_allowed"],
                "output": str(output_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
