from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
OUT = ROOT / "out" / "funding"
DRAFTS = OUT / "drafts"
SUBMISSIONS = OUT / "submissions_ready"
QUEUE_FILE = OUT / "funding_approval_queue.json"

RANKED_GRANTS_FILE = ROOT / "out" / "grants" / "grants_ranked_v2.json"
FALLBACK_RANKED_FILES = [
    ROOT / "out" / "institutional_grant_proposals.json",
    ROOT / "institutional_grant_proposals.json",
]
SECTOR_FILE = ROOT / "out" / "sector_value_matrix.json"
CROSS_FILE = ROOT / "out" / "cross_sector_optimization_report.json"
EVIDENCE_FILE = ROOT / "out" / "investor_and_grant_evidence.json"
INSTITUTIONAL_SUMMARY_FILE = ROOT / "institutional_summary.json"
API_KEY_REGISTRY_FILE = ROOT / "out" / "execution" / "api_key_registry_report.json"
KEY_SOURCE_OPPS_FILE = OUT / "key_source_opportunities.json"
GRANTS_API = "https://api.grants.gov/v1/api/search2"

# Opportunity policy: auto-approve queue items at creation time.
AUTO_APPROVE_ALWAYS = True
DEFAULT_APPROVAL_STATE = "APPROVED" if AUTO_APPROVE_ALWAYS else "PENDING_HUMAN_APPROVAL"
DEFAULT_QUEUE_STATUS = "APPROVED_READY" if AUTO_APPROVE_ALWAYS else "DRAFT_READY"
AUTO_APPROVAL_NOTE = "Auto-approved by policy"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _approval_seed() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "approval_state": DEFAULT_APPROVAL_STATE,
        "status": DEFAULT_QUEUE_STATUS,
    }
    if AUTO_APPROVE_ALWAYS:
        payload["approved_utc"] = now_utc()
        payload["reviewer_notes"] = AUTO_APPROVAL_NOTE
    return payload


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_queue() -> list[dict[str, Any]]:
    q = load_json(QUEUE_FILE, [])
    return q if isinstance(q, list) else []


def save_queue(queue: list[dict[str, Any]]) -> None:
    save_json(QUEUE_FILE, queue)


def _fmt_money(v: Any) -> str:
    try:
        n = float(v)
    except Exception:
        n = 0.0
    if abs(n) >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    if abs(n) >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n:.2f}"


def _bounded_number(
    value: Any,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    integer: bool = False,
) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    if integer:
        if not number.is_integer():
            return None
        return int(number)
    return number


def _metric_with_receipt(
    candidates: list[tuple[Path, str, Any]],
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    integer: bool = False,
) -> tuple[float | int | None, dict[str, str] | None]:
    for source_path, field, raw_value in candidates:
        value = _bounded_number(
            raw_value,
            minimum=minimum,
            maximum=maximum,
            integer=integer,
        )
        if value is None or not source_path.is_file():
            continue
        return value, {"source": str(source_path), "field": field}
    return None, None


def _validated_local_source_refs(raw_refs: Any) -> list[str]:
    refs = [raw_refs] if isinstance(raw_refs, str) else raw_refs
    if not isinstance(refs, list):
        return []

    validated: list[str] = []
    for raw_ref in refs:
        if not isinstance(raw_ref, str) or not raw_ref.strip():
            return []
        path = Path(raw_ref.strip())
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            return []
        resolved = str(path.resolve())
        if resolved not in validated:
            validated.append(resolved)
    return validated


def _unsupported_claim(reason: str) -> dict[str, Any]:
    return {"supported": False, "reason": reason, "source_refs": []}


def _benchmark_claim_support(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("supported") is not True:
        return _unsupported_claim("missing_explicit_claim_support")

    source_refs = _validated_local_source_refs(raw.get("source_refs"))
    if not source_refs:
        return _unsupported_claim("missing_or_invalid_local_source_refs")

    named_baseline = str(raw.get("named_baseline", "")).strip()
    if named_baseline.lower() in {"", "baseline", "generic baseline", "simple baseline", "incumbent", "sota"}:
        return _unsupported_claim("missing_named_baseline")

    metric = str(raw.get("metric", "")).strip()
    protocol_id = str(raw.get("protocol_id", "")).strip()
    direction = str(raw.get("direction", "")).strip().lower()
    candidate_value = _bounded_number(raw.get("candidate_value"))
    baseline_value = _bounded_number(raw.get("baseline_value"))
    if not metric or not protocol_id or candidate_value is None or baseline_value is None:
        return _unsupported_claim("missing_protocol_or_same_metric_values")
    if direction not in {"higher_is_better", "lower_is_better"}:
        return _unsupported_claim("missing_metric_direction")

    outperformed = (
        candidate_value > baseline_value
        if direction == "higher_is_better"
        else candidate_value < baseline_value
    )
    if not outperformed:
        return _unsupported_claim("candidate_does_not_outperform_named_baseline")

    return {
        "supported": True,
        "reason": "source_bound_same_protocol_comparison",
        "source_refs": source_refs,
        "named_baseline": named_baseline,
        "metric": metric,
        "protocol_id": protocol_id,
        "direction": direction,
        "candidate_value": candidate_value,
        "baseline_value": baseline_value,
    }


def _avoided_cost_claim_support(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("supported") is not True:
        return _unsupported_claim("missing_explicit_claim_support")

    source_refs = _validated_local_source_refs(raw.get("source_refs"))
    if not source_refs:
        return _unsupported_claim("missing_or_invalid_local_source_refs")

    claim_level = str(raw.get("claim_level", "")).strip().lower()
    if claim_level not in {"modeled_estimate", "measured_replay", "field_validated"}:
        return _unsupported_claim("missing_or_invalid_claim_level")
    amount_usd = _bounded_number(raw.get("amount_usd"), minimum=0.0)
    basis = str(raw.get("basis", "")).strip()
    if amount_usd is None or not basis:
        return _unsupported_claim("missing_amount_or_calculation_basis")

    return {
        "supported": True,
        "reason": "source_bound_avoided_cost_support",
        "source_refs": source_refs,
        "claim_level": claim_level,
        "amount_usd": amount_usd,
        "basis": basis,
    }


def _build_evidence_anchor() -> dict[str, Any]:
    sector = load_json(SECTOR_FILE, {})
    cross = load_json(CROSS_FILE, {})
    evidence = load_json(EVIDENCE_FILE, {})
    inst = load_json(INSTITUTIONAL_SUMMARY_FILE, {})

    cross_recommended = cross.get("recommended", {}) if isinstance(cross, dict) else {}
    if not isinstance(cross_recommended, dict):
        cross_recommended = {}

    yearly, yearly_receipt = _metric_with_receipt(
        [(SECTOR_FILE, "yearly_translated_value", sector.get("yearly_translated_value"))],
        minimum=0.0,
    )
    annual_upside, annual_upside_receipt = _metric_with_receipt(
        [
            (SECTOR_FILE, "annual_upside_usd", sector.get("annual_upside_usd")),
            (SECTOR_FILE, "modeled_annual_upside_usd", sector.get("modeled_annual_upside_usd")),
        ],
        minimum=0.0,
    )
    prevented, prevented_receipt = _metric_with_receipt(
        [
            (CROSS_FILE, "recommended.prevented_pct", cross_recommended.get("prevented_pct")),
            (CROSS_FILE, "prevented_pct", cross.get("prevented_pct")),
            (EVIDENCE_FILE, "prevented_pct", evidence.get("prevented_pct")),
        ],
        minimum=0.0,
        maximum=100.0,
    )
    sites, sites_receipt = _metric_with_receipt(
        [(EVIDENCE_FILE, "pilot_sites", evidence.get("pilot_sites"))],
        minimum=0.0,
        integer=True,
    )
    savings, savings_receipt = _metric_with_receipt(
        [(EVIDENCE_FILE, "savings_per_site_usd", evidence.get("savings_per_site_usd"))],
        minimum=0.0,
    )

    raw_claim_support = evidence.get("claim_support", {}) if isinstance(evidence, dict) else {}
    if not isinstance(raw_claim_support, dict):
        raw_claim_support = {}
    benchmark_claim = _benchmark_claim_support(raw_claim_support.get("benchmark_outperformance"))
    avoided_cost_claim = _avoided_cost_claim_support(raw_claim_support.get("avoided_cost"))

    metric_receipts = {
        key: receipt
        for key, receipt in {
            "yearly_translated_value_usd": yearly_receipt,
            "annual_upside_usd": annual_upside_receipt,
            "prevented_pct": prevented_receipt,
            "pilot_sites": sites_receipt,
            "savings_per_site_usd": savings_receipt,
        }.items()
        if receipt is not None
    }
    blockers = [
        f"missing_source_bound_metric:{key}"
        for key, value in {
            "yearly_translated_value_usd": yearly,
            "annual_upside_usd": annual_upside,
            "prevented_pct": prevented,
            "pilot_sites": sites,
            "savings_per_site_usd": savings,
        }.items()
        if value is None
    ]
    for claim_name, claim in {
        "benchmark_outperformance": benchmark_claim,
        "avoided_cost": avoided_cost_claim,
    }.items():
        if not claim["supported"]:
            blockers.append(f"unsupported_claim:{claim_name}:{claim['reason']}")

    return {
        "generated_utc": now_utc(),
        "economic_evidence_status": (
            "SOURCE_BOUND_ECONOMIC_SUPPORT_COMPLETE"
            if not blockers
            else "BLOCKED_MISSING_SOURCE_BOUND_ECONOMIC_SUPPORT"
        ),
        "yearly_translated_value_usd": yearly,
        "annual_upside_usd": annual_upside,
        "prevented_pct": prevented,
        "pilot_sites": sites,
        "savings_per_site_usd": savings,
        "metric_receipts": metric_receipts,
        "claim_support": {
            "benchmark_outperformance": benchmark_claim,
            "avoided_cost": avoided_cost_claim,
        },
        "evidence_blockers": blockers,
        "institutional_summary": inst,
        "sources": [
            str(SECTOR_FILE),
            str(CROSS_FILE),
            str(EVIDENCE_FILE),
            str(INSTITUTIONAL_SUMMARY_FILE),
        ],
    }


def _source_bound_metric_line(
    label: str,
    evidence: dict[str, Any],
    key: str,
    formatter,
) -> str:
    value = evidence.get(key)
    receipt = evidence.get("metric_receipts", {}).get(key)
    if value is None or not isinstance(receipt, dict):
        return f"- {label}: NOT ESTABLISHED (missing source-bound input)"
    return (
        f"- {label}: {formatter(value)} "
        f"(source: {receipt.get('source')}#{receipt.get('field')})"
    )


def _capability_narrative(evidence: dict[str, Any]) -> str:
    claim_support = evidence.get("claim_support", {})
    if not isinstance(claim_support, dict):
        claim_support = {}
    benchmark = claim_support.get("benchmark_outperformance", {})
    avoided_cost = claim_support.get("avoided_cost", {})

    lines = [
        (
            "LumenCore uses phase-locked harmonic optimization with Euclidean and "
            "non-Euclidean geometric scoring, physics-aware signal topology, and "
            "measurable risk controls."
        )
    ]
    if isinstance(benchmark, dict) and benchmark.get("supported") is True:
        lines.append(
            "Source-bound benchmark outperformance is limited to protocol "
            f"{benchmark['protocol_id']}: {benchmark['metric']} recorded "
            f"{benchmark['candidate_value']} for LumenCore versus "
            f"{benchmark['baseline_value']} for named baseline "
            f"{benchmark['named_baseline']} ({benchmark['direction']}). "
            f"Evidence: {', '.join(benchmark['source_refs'])}."
        )
    else:
        lines.append(
            "No source-bound benchmark-outperformance claim is made in this draft."
        )

    if isinstance(avoided_cost, dict) and avoided_cost.get("supported") is True:
        level = str(avoided_cost["claim_level"]).replace("_", " ")
        lines.append(
            f"A source-bound {level} avoided-cost amount of "
            f"{_fmt_money(avoided_cost['amount_usd'])} is recorded under the "
            f"stated basis: {avoided_cost['basis']}. Evidence: "
            f"{', '.join(avoided_cost['source_refs'])}. This is not a realized-savings "
            "claim and must remain within the cited calculation boundary."
        )
    else:
        lines.append(
            "No source-bound avoided-cost or realized-savings claim is made in this draft."
        )
    return "\n\n".join(lines)


def _ticket(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def _post_json(url: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    return json.loads(raw or "{}")


def _fetch_grantsgov(query: str, rows: int = 40) -> list[dict[str, Any]]:
    body = {
        "keyword": query,
        "rows": rows,
        "offset": 0,
        "oppStatuses": ["forecasted", "posted"],
        "sortBy": "openDate|desc",
    }
    data = _post_json(GRANTS_API, body)
    if isinstance(data, dict):
        for k in ("oppHits", "opportunities", "data", "results"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    if isinstance(data, list):
        return data
    return []


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    raw = str(s).strip()
    fmts = ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]
    for fmt in fmts:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def _days_to_close(hit: dict[str, Any]) -> int:
    raw = (
        hit.get("closeDate")
        or hit.get("close_date")
        or hit.get("closeDateTime")
        or hit.get("oppCloseDate")
    )
    dt = _parse_date(str(raw) if raw else None)
    if dt is None:
        return 9999
    delta = dt.astimezone(timezone.utc) - datetime.now(timezone.utc)
    return max(int(delta.total_seconds() // 86400), 0)


def _key_query_map() -> dict[str, list[str]]:
    return {
        "EIA_API_KEY": ["DOE grid modernization", "energy resilience", "critical infrastructure"],
        "FRED_API_KEY": ["economic resilience", "workforce innovation", "critical infrastructure"],
        "BLS_API_KEY": ["workforce modernization", "labor analytics", "economic resilience"],
        "BEA_API_KEY": ["regional economic development", "infrastructure modeling"],
        "CENSUS_API_KEY": ["community resilience", "smart infrastructure"],
        "NOAA_API_KEY": ["climate resilience", "weather risk mitigation", "grid resilience"],
        "NREL_API_KEY": ["renewable integration", "energy optimization", "grid reliability"],
        "EPA_AQS_KEY": ["air quality resilience", "environmental monitoring infrastructure"],
        "USGS_WATER_API_KEY": ["water resilience", "infrastructure risk analytics"],
        "NASA_API_KEY": ["space weather infrastructure", "advanced sensing systems"],
        "ALPHAVANTAGE_API_KEY": ["fintech infrastructure", "market stability analytics"],
    }


def _harvest_source_opportunities(max_rows_per_query: int = 30) -> list[dict[str, Any]]:
    reg = load_json(API_KEY_REGISTRY_FILE, {})
    rows = reg.get("rows", []) if isinstance(reg, dict) else []
    present = [r for r in rows if bool(r.get("present"))]
    mapping = _key_query_map()

    opps_by_num: dict[str, dict[str, Any]] = {}
    harvested: list[dict[str, Any]] = []

    for row in present:
        key = str(row.get("key", "")).strip().upper()
        if key not in mapping:
            continue
        queries = mapping[key]
        for q in queries:
            try:
                hits = _fetch_grantsgov(q, rows=max_rows_per_query)
            except (HTTPError, URLError, TimeoutError, ValueError):
                continue
            for hit in hits:
                opp_num = str(
                    hit.get("oppNum")
                    or hit.get("number")
                    or hit.get("opportunityNumber")
                    or hit.get("id")
                    or ""
                ).strip()
                if not opp_num:
                    continue
                if opp_num not in opps_by_num:
                    opps_by_num[opp_num] = hit
                harvested.append({
                    "key": key,
                    "query": q,
                    "opp_num": opp_num,
                    "title": hit.get("title") or hit.get("oppTitle") or "Untitled",
                    "agency": hit.get("agencyName") or hit.get("agency") or "Unknown",
                    "close_date": hit.get("closeDate") or hit.get("close_date") or hit.get("oppCloseDate"),
                    "days_to_close": _days_to_close(hit),
                    "award_ceiling_usd": float(
                        hit.get("awardCeiling")
                        or hit.get("awardCeilingAmt")
                        or hit.get("award_ceiling")
                        or 0.0
                    ),
                })

    # aggregate by opp
    agg: dict[str, dict[str, Any]] = {}
    for r in harvested:
        k = r["opp_num"]
        if k not in agg:
            agg[k] = {
                "opp_num": r["opp_num"],
                "title": r["title"],
                "agency": r["agency"],
                "close_date": r["close_date"],
                "days_to_close": r["days_to_close"],
                "award_ceiling_usd": r["award_ceiling_usd"],
                "matched_keys": [],
                "matched_queries": [],
            }
        if r["key"] not in agg[k]["matched_keys"]:
            agg[k]["matched_keys"].append(r["key"])
        if r["query"] not in agg[k]["matched_queries"]:
            agg[k]["matched_queries"].append(r["query"])
        agg[k]["days_to_close"] = min(int(agg[k]["days_to_close"]), int(r["days_to_close"]))
        agg[k]["award_ceiling_usd"] = max(float(agg[k]["award_ceiling_usd"]), float(r["award_ceiling_usd"]))

    out = list(agg.values())
    for item in out:
        urgency = max(0, 60 - min(int(item["days_to_close"]), 60))
        key_fit = len(item["matched_keys"]) * 10
        size = 12 if float(item.get("award_ceiling_usd", 0.0)) >= 500_000 else 0
        item["priority_score"] = round(70 + urgency + key_fit + size, 2)

    out.sort(key=lambda x: x["priority_score"], reverse=True)
    save_json(KEY_SOURCE_OPPS_FILE, {
        "generated_utc": now_utc(),
        "source": "api_key_registry + grants.gov",
        "count": len(out),
        "rows": out,
    })
    return out


def _grant_items(top: int, no_network: bool) -> list[dict[str, Any]]:
    if not RANKED_GRANTS_FILE.exists() and not no_network:
        cmd = [
            sys.executable,
            str(CODE / "grant_hunter_v2.py"),
            "--profile",
            str(CODE / "grants_profile_lumencore.json"),
            "hunt",
            "--rows",
            "180",
            "--top",
            str(max(top, 12)),
        ]
        subprocess.run(cmd, check=False, cwd=str(ROOT))

    ranked: list[dict[str, Any]] = []
    ranked_bundle = load_json(RANKED_GRANTS_FILE, {})
    if isinstance(ranked_bundle, dict):
        ranked = ranked_bundle.get("ranked", []) or []

    if not ranked:
        for fp in FALLBACK_RANKED_FILES:
            alt = load_json(fp, {})
            if isinstance(alt, dict):
                if isinstance(alt.get("ranked"), list):
                    ranked = alt.get("ranked", [])
                    break
                if isinstance(alt.get("proposals"), list):
                    ranked = alt.get("proposals", [])
                    break

    items: list[dict[str, Any]] = []
    for row in ranked[:top]:
        score = float(row.get("final_score", 0.0) or 0.0)
        days = int(row.get("days_to_close", 9999) or 9999)
        ticket = _ticket("FUND-GRANT")
        items.append(
            {
                "ticket_id": ticket,
                "channel": "grant",
                "title": row.get("title", "Untitled Grant Opportunity"),
                "agency": row.get("agency", "Unknown"),
                "opportunity_id": row.get("opp_num", ""),
                "priority_score": round(score, 3),
                "days_to_deadline": days,
                "deadline_utc": row.get("close_date"),
                **_approval_seed(),
                "created_utc": now_utc(),
                "estimated_value_usd": float(row.get("award_ceiling_usd", 0.0) or 0.0),
                "reason": row.get("reasons", []),
            }
        )
    return items


def _grant_items_from_keys(top: int, no_network: bool) -> list[dict[str, Any]]:
    if no_network:
        pack = load_json(KEY_SOURCE_OPPS_FILE, {})
        rows = pack.get("rows", []) if isinstance(pack, dict) else []
    else:
        rows = _harvest_source_opportunities(max_rows_per_query=24)

    out: list[dict[str, Any]] = []
    for row in rows[:top]:
        out.append({
            "ticket_id": _ticket("FUND-SRC"),
            "channel": "grant_source_direct",
            "title": row.get("title", "Untitled Opportunity"),
            "agency": row.get("agency", "Unknown"),
            "opportunity_id": row.get("opp_num", ""),
            "priority_score": float(row.get("priority_score", 0.0) or 0.0),
            "days_to_deadline": int(row.get("days_to_close", 9999) or 9999),
            "deadline_utc": row.get("close_date"),
            **_approval_seed(),
            "created_utc": now_utc(),
            "estimated_value_usd": float(row.get("award_ceiling_usd", 0.0) or 0.0),
            "reason": [
                "Matched via live configured key sources",
                f"Key alignment: {', '.join(row.get('matched_keys', [])[:5])}",
                f"Queries: {', '.join(row.get('matched_queries', [])[:3])}",
            ],
            "source_keys": row.get("matched_keys", []),
            "source_queries": row.get("matched_queries", []),
        })
    return out


def _contract_items() -> list[dict[str, Any]]:
    # High-fit targets derived from current evidence lane.
    targets = [
        ("DOE Grid Modernization Service Contract", "Department of Energy", 2_500_000.0, 21),
        ("DHS Critical Infrastructure Resilience Pilot", "Department of Homeland Security", 1_750_000.0, 18),
        ("DoD Predictive Infrastructure Readiness Contract", "Department of Defense", 3_200_000.0, 24),
    ]
    out = []
    for title, agency, val, days in targets:
        out.append(
            {
                "ticket_id": _ticket("FUND-CONTRACT"),
                "channel": "contract",
                "title": title,
                "agency": agency,
                "opportunity_id": "direct_outreach",
                "priority_score": round(88.0 + (30 - min(days, 30)) * 0.4, 2),
                "days_to_deadline": days,
                "deadline_utc": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(),
                **_approval_seed(),
                "created_utc": now_utc(),
                "estimated_value_usd": val,
                "reason": ["Evidence-backed fit", "Fast-track outreach packet ready"],
            }
        )
    return out


def _loan_items() -> list[dict[str, Any]]:
    options = [
        ("SBA 7(a) Working Capital", "SBA", 750_000.0, 14),
        ("SBA 504 Equipment/Infrastructure", "SBA", 1_500_000.0, 20),
        ("DOE LPO Pre-Application", "DOE Loan Programs Office", 5_000_000.0, 28),
    ]
    rows = []
    for title, agency, val, days in options:
        rows.append(
            {
                "ticket_id": _ticket("FUND-LOAN"),
                "channel": "loan",
                "title": title,
                "agency": agency,
                "opportunity_id": "capital_program",
                "priority_score": round(84.0 + (30 - min(days, 30)) * 0.35, 2),
                "days_to_deadline": days,
                "deadline_utc": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(),
                **_approval_seed(),
                "created_utc": now_utc(),
                "estimated_value_usd": val,
                "reason": ["Non-dilutive or low-dilution capital", "Matches infrastructure deployment roadmap"],
            }
        )
    return rows


def _crowdfunding_items() -> list[dict[str, Any]]:
    options = [
        ("Reg CF Equity Raise", "Wefunder / Republic", 750_000.0, 21),
        ("Kickstarter Hardware Launch", "Kickstarter", 250_000.0, 18),
        ("Indiegogo Founders Campaign", "Indiegogo", 350_000.0, 20),
    ]
    rows = []
    for title, agency, val, days in options:
        rows.append(
            {
                "ticket_id": _ticket("FUND-CROWD"),
                "channel": "crowdfund",
                "title": title,
                "agency": agency,
                "opportunity_id": "crowdfunding_campaign",
                "priority_score": round(82.0 + (30 - min(days, 30)) * 0.42, 2),
                "days_to_deadline": days,
                "deadline_utc": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(),
                **_approval_seed(),
                "created_utc": now_utc(),
                "estimated_value_usd": val,
                "reason": [
                    "Community-backed capital lane with founder-credibility signaling",
                    "Fits rapid pilot narrative and pre-order style validation",
                ],
            }
        )
    return rows


def _write_draft(item: dict[str, Any], evidence: dict[str, Any]) -> dict[str, str]:
    DRAFTS.mkdir(parents=True, exist_ok=True)
    tid = item["ticket_id"]
    md_path = DRAFTS / f"{tid}.md"
    json_path = DRAFTS / f"{tid}.json"
    economic_status = str(
        evidence.get(
            "economic_evidence_status",
            "BLOCKED_MISSING_SOURCE_BOUND_ECONOMIC_SUPPORT",
        )
    )
    blockers = evidence.get("evidence_blockers", [])
    if not isinstance(blockers, list):
        blockers = ["invalid_evidence_blocker_payload"]
    blocker_lines = (
        "\n".join(f"- {blocker}" for blocker in blockers)
        if blockers
        else "- None; declared source-bound economic support is complete."
    )

    body = f"""# Funding Draft: {item['title']}

- Ticket: {item['ticket_id']}
- Channel: {item['channel']}
- Agency/Lender: {item['agency']}
- Priority Score: {item['priority_score']}
- Deadline UTC: {item['deadline_utc']}
- Estimated Value: {_fmt_money(item.get('estimated_value_usd', 0.0))}
- Economic Evidence Status: {economic_status}

## Evidence Anchor
{_source_bound_metric_line('Annual translated value surface', evidence, 'yearly_translated_value_usd', _fmt_money)}
{_source_bound_metric_line('Annual upside', evidence, 'annual_upside_usd', _fmt_money)}
{_source_bound_metric_line('Failure prevention rate', evidence, 'prevented_pct', lambda value: f'{float(value):.1f}%')}
{_source_bound_metric_line('Pilot footprint', evidence, 'pilot_sites', lambda value: f'{int(value)} sites')}
{_source_bound_metric_line('Savings per site/year', evidence, 'savings_per_site_usd', _fmt_money)}

## Capability Narrative
{_capability_narrative(evidence)}

## Evidence Blockers
{blocker_lines}

## Requested Decision
- Approve for submission: YES / NO
- Reviewer notes:

"""
    md_path.write_text(body, encoding="utf-8")

    payload = {"item": item, "evidence": evidence, "draft_markdown": str(md_path), "generated_utc": now_utc()}
    save_json(json_path, payload)
    return {"markdown": str(md_path), "json": str(json_path)}


def cmd_build(args: argparse.Namespace) -> int:
    evidence = _build_evidence_anchor()
    queue = load_queue()

    channels = {c.strip().lower() for c in (args.channels or "grant,key-source,contract,loan,crowdfund").split(",") if c.strip()}
    new_items: list[dict[str, Any]] = []

    if "grant" in channels:
        new_items.extend(_grant_items(args.top, args.no_network))
    if "key-source" in channels:
        new_items.extend(_grant_items_from_keys(args.top, args.no_network))
    if "contract" in channels:
        new_items.extend(_contract_items())
    if "loan" in channels:
        new_items.extend(_loan_items())
    if "crowdfund" in channels:
        new_items.extend(_crowdfunding_items())

    # Dedupe by (channel,title)
    existing_keys = {(str(i.get("channel", "")).lower(), str(i.get("title", "")).strip().lower()) for i in queue}
    created = 0
    for item in new_items:
        key = (item["channel"], item["title"].strip().lower())
        if key in existing_keys:
            continue
        drafts = _write_draft(item, evidence)
        item["draft_files"] = drafts
        queue.append(item)
        existing_keys.add(key)
        created += 1

    save_queue(queue)
    print(json.dumps({
        "status": "ok",
        "created": created,
        "queue_count": len(queue),
        "queue_file": str(QUEUE_FILE),
    }, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    queue = load_queue()
    print(f"queue_count={len(queue)}")
    for item in queue[: args.limit]:
        print(
            f"{item.get('approval_state','?'):>22}  {item.get('ticket_id','?'):22}  "
            f"{item.get('channel','?'):8}  d={item.get('days_to_deadline','?'):>3}  "
            f"{item.get('title','')[:70]}"
        )
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    queue = load_queue()
    found = False
    for item in queue:
        if item.get("ticket_id") == args.ticket:
            item["approval_state"] = "APPROVED"
            item["approved_utc"] = now_utc()
            item["reviewer_notes"] = args.notes or "Approved"
            found = True
            break
    if not found:
        print(json.dumps({"status": "error", "detail": f"ticket not found: {args.ticket}"}, indent=2))
        return 1
    save_queue(queue)
    print(json.dumps({"status": "ok", "ticket": args.ticket, "state": "APPROVED"}, indent=2))
    return 0


def cmd_auto_approve_all(args: argparse.Namespace) -> int:
    queue = load_queue()
    updated = 0
    for item in queue:
        state = str(item.get("approval_state", "")).upper()
        if state != "PENDING_HUMAN_APPROVAL":
            continue
        item["approval_state"] = "APPROVED"
        item["approved_utc"] = now_utc()
        item["reviewer_notes"] = args.notes or AUTO_APPROVAL_NOTE
        if str(item.get("status", "")).upper() == "DRAFT_READY":
            item["status"] = "APPROVED_READY"
        updated += 1

    save_queue(queue)
    print(json.dumps({
        "status": "ok",
        "updated": updated,
        "queue_count": len(queue),
        "queue_file": str(QUEUE_FILE),
    }, indent=2))
    return 0


def cmd_ship(args: argparse.Namespace) -> int:
    queue = load_queue()
    target = None
    for item in queue:
        if item.get("ticket_id") == args.ticket:
            target = item
            break
    if target is None:
        print(json.dumps({"status": "error", "detail": f"ticket not found: {args.ticket}"}, indent=2))
        return 1
    if str(target.get("approval_state", "")).upper() != "APPROVED":
        print(json.dumps({"status": "error", "detail": "ticket must be APPROVED before ship"}, indent=2))
        return 1

    SUBMISSIONS.mkdir(parents=True, exist_ok=True)
    sid = f"SUBMIT-{args.ticket}"
    out_file = SUBMISSIONS / f"{sid}.json"
    target["approval_state"] = "SHIPPED"
    target["shipped_utc"] = now_utc()
    target["shipping_channel"] = args.channel

    payload = {
        "submission_id": sid,
        "generated_utc": now_utc(),
        "shipping_channel": args.channel,
        "ticket": target,
        "instructions": {
            "next_action": "Send packet using agency portal or lender portal with attached draft files",
            "attachment_paths": target.get("draft_files", {}),
        },
    }
    save_json(out_file, payload)
    save_queue(queue)

    print(json.dumps({
        "status": "ok",
        "ticket": args.ticket,
        "state": "SHIPPED",
        "submission_manifest": str(out_file),
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Funding Autopilot: grants + contracts + loans + crowdfunding")
    sub = p.add_subparsers(dest="command", required=True)

    pb = sub.add_parser("build", help="Create new approval-ready funding drafts")
    pb.add_argument("--top", type=int, default=10)
    pb.add_argument("--channels", default="grant,key-source,contract,loan,crowdfund")
    pb.add_argument("--no-network", action="store_true", help="Do not call Grants.gov hunt if ranked file is absent")
    pb.set_defaults(func=cmd_build)

    ph = sub.add_parser("harvest-from-keys", help="Crawl source-aligned opportunities from live key registry")
    ph.add_argument("--rows", type=int, default=24)
    ph.set_defaults(func=lambda args: (print(json.dumps({"status": "ok", "count": len(_harvest_source_opportunities(max_rows_per_query=args.rows)), "output": str(KEY_SOURCE_OPPS_FILE)}, indent=2)), 0)[1])

    pl = sub.add_parser("list", help="List queue items")
    pl.add_argument("--limit", type=int, default=100)
    pl.set_defaults(func=cmd_list)

    pa = sub.add_parser("approve", help="Approve ticket")
    pa.add_argument("--ticket", required=True)
    pa.add_argument("--notes", default="")
    pa.set_defaults(func=cmd_approve)

    paa = sub.add_parser("auto-approve-all", help="Approve all pending queue tickets")
    paa.add_argument("--notes", default=AUTO_APPROVAL_NOTE)
    paa.set_defaults(func=cmd_auto_approve_all)

    ps = sub.add_parser("ship", help="Ship approved ticket")
    ps.add_argument("--ticket", required=True)
    ps.add_argument("--channel", default="portal_manual_submit")
    ps.set_defaults(func=cmd_ship)

    return p


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
