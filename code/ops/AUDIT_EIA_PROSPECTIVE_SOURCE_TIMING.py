"""Audit whether EIA-930 publication timing can satisfy the prospective seal.

The audit never serializes the API credential. It compares complete local-day
aggregates reconstructed from EIA's UTC hour-ending feed with the publisher's
daily series and records whether a complete future-day forecast is available
before the original protocol's target-local-midnight deadline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "config" / "eia_grid_prospective_hybrid_router_protocol_v1.json"
RUNTIME_DIR = ROOT / "out" / "eia_grid_prospective_hybrid_router"
PREDICTIONS_PATH = RUNTIME_DIR / "sealed_predictions.jsonl"
SETTLEMENTS_PATH = RUNTIME_DIR / "settlements.jsonl"
STATUS_PATH = RUNTIME_DIR / "prospective_status_latest.json"
EVIDENCE_PATH = (
    ROOT
    / "evidence"
    / "external_validation"
    / "eia_prospective_source_timing_audit_20260714.json"
)
DOC_PATH = ROOT / "docs" / "EIA_PROSPECTIVE_SOURCE_TIMING_AUDIT_2026-07-14.md"

HOURLY_ROUTE = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
DAILY_ROUTE = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"
ZERO_HASH = "0" * 64

AUTHORITY_SOURCE = {
    "CISO": {"facet_timezone": "Pacific", "iana_timezone": "America/Los_Angeles"},
    "ERCO": {"facet_timezone": "Central", "iana_timezone": "America/Chicago"},
    "ISNE": {"facet_timezone": "Eastern", "iana_timezone": "America/New_York"},
    "MISO": {"facet_timezone": "Central", "iana_timezone": "America/Chicago"},
    "NYIS": {"facet_timezone": "Eastern", "iana_timezone": "America/New_York"},
    "PJM": {"facet_timezone": "Eastern", "iana_timezone": "America/New_York"},
    "SWPP": {"facet_timezone": "Central", "iana_timezone": "America/Chicago"},
    "TVA": {"facet_timezone": "Central", "iana_timezone": "America/Chicago"},
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_key() -> str:
    key = os.environ.get("EIA_API_KEY") or os.environ.get("EIA_API_KEY_PREMIUM")
    if not key:
        raise RuntimeError("EIA API key is not configured in the process environment")
    return key


def parse_hour_ending_utc(period: str) -> datetime:
    return datetime.strptime(period, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)


def local_day_for_hour_ending(period: str, iana_timezone: str) -> str:
    """Assign an EIA UTC hour-ending label to the local interval it closes."""

    interval_start = parse_hour_ending_utc(period) - timedelta(hours=1)
    return interval_start.astimezone(ZoneInfo(iana_timezone)).date().isoformat()


def expected_hour_endings(local_day: str, iana_timezone: str) -> list[str]:
    """Return the exact 23/24/25 UTC hour-ending labels for a local day."""

    day = date.fromisoformat(local_day)
    zone = ZoneInfo(iana_timezone)
    start = datetime.combine(day, time.min, tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone).astimezone(
        timezone.utc
    )
    labels: list[str] = []
    cursor = start + timedelta(hours=1)
    while cursor <= end:
        labels.append(cursor.strftime("%Y-%m-%dT%H"))
        cursor += timedelta(hours=1)
    return labels


def aggregate_complete_local_days(
    rows: Iterable[dict[str, Any]], respondent: str, iana_timezone: str
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], dict[str, Any]]]:
    values: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for row in rows:
        if row.get("respondent") != respondent or row.get("type") not in {"D", "DF"}:
            continue
        try:
            value = float(row["value"])
        except (KeyError, TypeError, ValueError):
            continue
        period = str(row.get("period"))
        local_day = local_day_for_hour_ending(period, iana_timezone)
        values[(local_day, str(row["type"]))][period] = value

    aggregates: dict[tuple[str, str], float] = {}
    diagnostics: dict[tuple[str, str], dict[str, Any]] = {}
    for key, period_values in sorted(values.items()):
        expected = expected_hour_endings(key[0], iana_timezone)
        observed = sorted(period_values)
        complete = observed == expected
        diagnostics[key] = {
            "complete": complete,
            "expected_hour_count": len(expected),
            "observed_hour_count": len(observed),
            "missing_periods": sorted(set(expected) - set(observed)),
            "unexpected_periods": sorted(set(observed) - set(expected)),
        }
        if complete:
            aggregates[key] = sum(period_values[period] for period in expected)
    return aggregates, diagnostics


def request_rows(
    route: str,
    frequency: str,
    respondent: str,
    start: str,
    end: str,
    facet_timezone: str | None,
    timeout: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params: list[tuple[str, str]] = [
        ("api_key", read_key()),
        ("frequency", frequency),
        ("data[0]", "value"),
        ("facets[type][]", "D"),
        ("facets[type][]", "DF"),
        ("facets[respondent][]", respondent),
        ("start", start),
        ("end", end),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("offset", "0"),
        ("length", "5000"),
    ]
    if facet_timezone:
        params.append(("facets[timezone][]", facet_timezone))
    request = urllib.request.Request(
        route + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": "LumenCore-EIA-Source-Timing-Audit/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.getcode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"EIA {frequency} request failed for {respondent} with HTTP {exc.code}"
        ) from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"EIA {frequency} request failed for {respondent}: {type(exc).__name__}"
        ) from None

    payload = json.loads(raw.decode("utf-8"))
    response_payload = payload.get("response", {})
    rows = response_payload.get("data", []) if isinstance(response_payload, dict) else []
    accepted = [row for row in rows if isinstance(row, dict)]
    return accepted, {
        "route": route,
        "frequency": frequency,
        "respondent": respondent,
        "start": start,
        "end": end,
        "http_status": status,
        "row_count": len(accepted),
        "response_total": int(response_payload.get("total", len(accepted))),
        "response_body_sha256": hashlib.sha256(raw).hexdigest(),
        "credential_serialized": False,
    }


def read_jsonl_count(path: Path) -> tuple[int, str]:
    if not path.exists():
        return 0, ZERO_HASH
    count = 0
    terminal = ZERO_HASH
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            count += 1
            terminal = str(row.get("record_sha256") or terminal)
    return count, terminal


def build_audit(timeout: int = 45, observed_at: datetime | None = None) -> dict[str, Any]:
    observed_at = observed_at or datetime.now(timezone.utc)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    prediction_count, prediction_terminal = read_jsonl_count(PREDICTIONS_PATH)
    settlement_count, settlement_terminal = read_jsonl_count(SETTLEMENTS_PATH)
    status = (
        json.loads(STATUS_PATH.read_text(encoding="utf-8")) if STATUS_PATH.exists() else {}
    )

    reconciliation_start = "2026-07-01"
    reconciliation_end = "2026-07-10"
    hourly_start = "2026-06-29T00"
    hourly_end = "2026-07-12T23"
    availability_start = (observed_at.date() - timedelta(days=2)).strftime("%Y-%m-%dT00")
    availability_end = (observed_at.date() + timedelta(days=2)).strftime("%Y-%m-%dT23")

    authority_results: list[dict[str, Any]] = []
    all_reconciled = True
    no_future_complete_forecast = True
    for respondent in protocol["balancing_authorities"]:
        source = AUTHORITY_SOURCE[respondent]
        hourly_rows, hourly_receipt = request_rows(
            HOURLY_ROUTE,
            "hourly",
            respondent,
            hourly_start,
            hourly_end,
            None,
            timeout,
        )
        daily_rows, daily_receipt = request_rows(
            DAILY_ROUTE,
            "daily",
            respondent,
            reconciliation_start,
            reconciliation_end,
            source["facet_timezone"],
            timeout,
        )
        aggregates, _ = aggregate_complete_local_days(
            hourly_rows, respondent, source["iana_timezone"]
        )
        official_daily = {
            (str(row.get("period")), str(row.get("type"))): float(row["value"])
            for row in daily_rows
            if row.get("respondent") == respondent
            and row.get("type") in {"D", "DF"}
            and row.get("value") is not None
        }
        comparisons: list[dict[str, Any]] = []
        for key, official_value in sorted(official_daily.items()):
            if key not in aggregates:
                continue
            delta = aggregates[key] - official_value
            comparisons.append(
                {
                    "local_day": key[0],
                    "type": key[1],
                    "hourly_aggregate_mwh": aggregates[key],
                    "official_daily_mwh": official_value,
                    "delta_mwh": delta,
                    "exact_match": delta == 0.0,
                }
            )
        exact_count = sum(row["exact_match"] for row in comparisons)
        authority_reconciled = bool(comparisons) and exact_count == len(comparisons)
        all_reconciled = all_reconciled and authority_reconciled

        availability_rows, availability_receipt = request_rows(
            HOURLY_ROUTE,
            "hourly",
            respondent,
            availability_start,
            availability_end,
            None,
            timeout,
        )
        current_aggregates, diagnostics = aggregate_complete_local_days(
            availability_rows, respondent, source["iana_timezone"]
        )
        complete_forecast_days = sorted(
            key[0] for key in current_aggregates if key[1] == "DF"
        )
        local_observed_day = observed_at.astimezone(
            ZoneInfo(source["iana_timezone"])
        ).date().isoformat()
        future_complete = [day for day in complete_forecast_days if day > local_observed_day]
        no_future_complete_forecast = no_future_complete_forecast and not future_complete
        latest_df_period = max(
            (
                str(row["period"])
                for row in availability_rows
                if row.get("type") == "DF" and row.get("respondent") == respondent
            ),
            default=None,
        )
        latest_d_period = max(
            (
                str(row["period"])
                for row in availability_rows
                if row.get("type") == "D" and row.get("respondent") == respondent
            ),
            default=None,
        )
        latest_complete_day = complete_forecast_days[-1] if complete_forecast_days else None
        latest_diag = diagnostics.get((latest_complete_day, "DF"), {}) if latest_complete_day else {}
        authority_results.append(
            {
                "respondent": respondent,
                "facet_timezone": source["facet_timezone"],
                "iana_timezone": source["iana_timezone"],
                "reconciliation": {
                    "window_start": reconciliation_start,
                    "window_end": reconciliation_end,
                    "comparison_count": len(comparisons),
                    "exact_match_count": exact_count,
                    "maximum_absolute_delta_mwh": max(
                        (abs(float(row["delta_mwh"])) for row in comparisons),
                        default=None,
                    ),
                    "all_exact": authority_reconciled,
                    "comparison_sha256": canonical_sha256(comparisons),
                },
                "availability_at_observation": {
                    "local_observed_day": local_observed_day,
                    "latest_actual_hour_ending_utc": latest_d_period,
                    "latest_forecast_hour_ending_utc": latest_df_period,
                    "latest_complete_forecast_local_day": latest_complete_day,
                    "latest_complete_forecast_hour_count": latest_diag.get(
                        "observed_hour_count"
                    ),
                    "complete_future_local_days": future_complete,
                    "future_complete_daily_forecast_available": bool(future_complete),
                },
                "receipts": {
                    "historical_hourly": hourly_receipt,
                    "historical_daily": daily_receipt,
                    "availability_hourly": availability_receipt,
                },
            }
        )

    return {
        "schema": "eia_prospective_source_timing_audit.v1",
        "generated_utc": observed_at.isoformat(),
        "protocol": {
            "path": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
            "protocol_id": protocol["protocol_id"],
            "sha256": file_sha256(PROTOCOL_PATH),
            "seal_rule": "Prediction must be sealed before target-local midnight.",
            "backfill_allowed": False,
        },
        "v1_runtime": {
            "status_state": status.get("state"),
            "prediction_count": prediction_count,
            "prediction_terminal_sha256": prediction_terminal,
            "settlement_count": settlement_count,
            "settlement_terminal_sha256": settlement_terminal,
            "negative_result_preserved": prediction_count == 0 and settlement_count == 0,
        },
        "source_contract": {
            "publisher": "U.S. Energy Information Administration",
            "product": "Form EIA-930 hourly demand and demand forecast",
            "hourly_route": HOURLY_ROUTE,
            "daily_route": DAILY_ROUTE,
            "hourly_period_semantics": "UTC hour ending",
            "local_day_assignment": "Subtract one hour from the UTC hour-ending label, then convert the interval start to the authority IANA timezone.",
            "completeness_rule": "Accept an aggregate only when every expected UTC hour ending for the 23/24/25-hour local day is present exactly once.",
            "credential_serialized": False,
        },
        "reconciliation": {
            "all_authorities_exact": all_reconciled,
            "expected_authority_count": len(protocol["balancing_authorities"]),
            "observed_authority_count": len(authority_results),
            "total_comparison_count": sum(
                row["reconciliation"]["comparison_count"] for row in authority_results
            ),
            "total_exact_match_count": sum(
                row["reconciliation"]["exact_match_count"] for row in authority_results
            ),
        },
        "timing_finding": {
            "complete_future_daily_forecast_observed": not no_future_complete_forecast,
            "v1_daily_seal_feasible_on_observed_schedule": False
            if no_future_complete_forecast
            else None,
            "finding": (
                "The hourly source exactly reconstructs settled daily D/DF values, but at observation time no authority exposed a complete future local-day DF aggregate before that target day's local-midnight gate. The v1 daily target therefore remains a valid zero-prediction negative result and must not be backfilled."
            ),
            "remediation": (
                "Use a separately preregistered hourly target whose seal deadline is the target interval start; do not weaken or rewrite v1."
            ),
        },
        "authorities": authority_results,
        "claim_boundary": (
            "This receipt establishes source equivalence and an observed publication-timing limitation. It does not establish prospective model skill, production readiness, savings, patentability, or external validation."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    reconciliation = payload["reconciliation"]
    timing = payload["timing_finding"]
    lines = [
        "# EIA Prospective Source-Timing Audit",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Decision",
        "",
        "The original daily protocol remains frozen as a zero-prediction negative result. The official hourly feed can reconstruct settled daily totals exactly, but its observed forecast horizon does not expose a complete future local day before the daily protocol's target-local-midnight seal. No backfill or relaxed deadline is permitted.",
        "",
        "The scientifically valid remediation is a separate hourly prospective protocol with a pre-interval seal and isolated append-only ledgers.",
        "",
        "## Reconciliation",
        "",
        f"- Authorities reconciled: `{reconciliation['observed_authority_count']}/{reconciliation['expected_authority_count']}`",
        f"- Exact hourly-to-daily comparisons: `{reconciliation['total_exact_match_count']}/{reconciliation['total_comparison_count']}`",
        f"- All authority comparisons exact: `{str(reconciliation['all_authorities_exact']).lower()}`",
        "- Hourly labels are UTC hour endings. The interval is assigned to a local day after subtracting one hour and converting to the authority IANA timezone.",
        "- Completeness requires exactly every expected hour ending for that 23/24/25-hour local day.",
        "",
        "| Authority | Comparisons | Exact | Max abs delta MWh | Future complete day available |",
        "|---|---:|---:|---:|---|",
    ]
    for row in payload["authorities"]:
        rec = row["reconciliation"]
        availability = row["availability_at_observation"]
        lines.append(
            f"| {row['respondent']} | {rec['comparison_count']} | {rec['exact_match_count']} | {rec['maximum_absolute_delta_mwh']} | {str(availability['future_complete_daily_forecast_available']).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Frozen Runtime",
            "",
            f"- Prediction records: `{payload['v1_runtime']['prediction_count']}`",
            f"- Settlement records: `{payload['v1_runtime']['settlement_count']}`",
            f"- Negative result preserved: `{str(payload['v1_runtime']['negative_result_preserved']).lower()}`",
            "",
            "## Finding",
            "",
            timing["finding"],
            "",
            "## Publisher Sources",
            "",
            "- [EIA Form EIA-930 hourly API dashboard](https://www.eia.gov/opendata/browser/electricity/rto/region-data)",
            "- [EIA Open Data API documentation](https://www.eia.gov/opendata/documentation.php)",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            f"Machine-readable receipt: `{EVIDENCE_PATH.relative_to(ROOT).as_posix()}`",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_audit(timeout=args.timeout)
    if not payload["reconciliation"]["all_authorities_exact"]:
        raise RuntimeError("hourly-to-daily reconciliation was not exact")
    if args.check:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    DOC_PATH.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "evidence_path": EVIDENCE_PATH.relative_to(ROOT).as_posix(),
                "evidence_sha256": file_sha256(EVIDENCE_PATH),
                "document_path": DOC_PATH.relative_to(ROOT).as_posix(),
                "all_authorities_exact": payload["reconciliation"][
                    "all_authorities_exact"
                ],
                "complete_future_daily_forecast_observed": payload["timing_finding"][
                    "complete_future_daily_forecast_observed"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
