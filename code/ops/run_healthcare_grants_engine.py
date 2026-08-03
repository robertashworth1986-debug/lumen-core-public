from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_OPPORTUNITIES = ROOT / "out" / "opportunities"
OUT_GRANTS = ROOT / "out" / "grants"
OUT_DIR = ROOT / "out" / "ops" / "healthcare_grants_engine"


HEALTHCARE_KEYWORD_WEIGHTS: dict[str, float] = {
    "health": 6.0,
    "healthcare": 8.0,
    "public health": 9.0,
    "clinical": 9.0,
    "clinical trial": 10.0,
    "medical": 9.0,
    "medicine": 9.0,
    "biomedical": 10.0,
    "biotech": 8.0,
    "patient": 8.0,
    "hospital": 8.0,
    "care": 5.0,
    "disease": 8.0,
    "diagnostic": 8.0,
    "mental health": 10.0,
    "behavioral health": 9.0,
    "telehealth": 8.0,
    "diabetes": 9.0,
    "epidemiology": 9.0,
    "medicaid": 8.0,
    "medicare": 8.0,
    "fda": 8.0,
    "nih": 11.0,
    "hhs": 10.0,
    "cdc": 10.0,
    "cms": 9.0,
    "ahrq": 9.0,
    "nursing": 7.0,
    "maternal": 8.0,
    "vaccine": 8.0,
    "substance use": 9.0,
    "opioid": 9.0,
    "health equity": 8.0,
    "rural health": 8.0,
    "infection": 7.0,
}


AGENCY_HEALTH_BONUS: dict[str, float] = {
    "national institutes of health": 20.0,
    "nih": 20.0,
    "department of health and human services": 18.0,
    "hhs": 18.0,
    "centers for disease control": 16.0,
    "cdc": 16.0,
    "centers for medicare": 14.0,
    "cms": 14.0,
    "food and drug administration": 12.0,
    "fda": 12.0,
    "indian health service": 12.0,
    "iha": 10.0,
}


SCIENCE_KEYWORD_WEIGHTS: dict[str, float] = {
    "research": 6.0,
    "r01": 10.0,
    "r21": 8.0,
    "u24": 8.0,
    "phase i": 6.0,
    "phase ii": 6.0,
    "pilot": 6.0,
    "model": 5.0,
    "algorithm": 5.0,
    "randomized": 8.0,
    "double-blind": 8.0,
    "trial": 8.0,
    "cohort": 6.0,
    "endpoint": 5.0,
    "validation": 6.0,
    "evidence": 5.0,
}


DATE_FORMATS = (
    "%m/%d/%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m-%d-%Y",
    "%m/%d/%y",
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def strip_html(value: Any) -> str:
    raw = str(value or "")
    without_tags = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(re.sub(r"\s+", " ", without_tags)).strip()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if normalize_text(text) in {"none", "null", "na", "n/a"}:
        return None
    cleaned = text.replace("$", "").replace(",", "")
    try:
        return float(cleaned)
    except Exception:
        return None


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if normalize_text(text) in {"none", "null", "na", "n/a"}:
        return None
    try:
        return int(float(text))
    except Exception:
        return None


def parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def days_to_close(close_date: Any) -> int | None:
    dt = parse_date(close_date)
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    return int((dt.date() - now.date()).days)


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def collect_source_files() -> list[Path]:
    files: list[Path] = []
    ranked_path = OUT_OPPORTUNITIES / "ranked.json"
    if ranked_path.exists():
        files.append(ranked_path)

    harvest_candidates = sorted(OUT_OPPORTUNITIES.glob("harvest_*.json"))
    if harvest_candidates:
        files.append(harvest_candidates[-1])

    grants_ranked_path = OUT_GRANTS / "grants_ranked_v2.json"
    if grants_ranked_path.exists():
        files.append(grants_ranked_path)

    return files


def normalize_record(record: dict[str, Any], source_channel: str, source_file: Path) -> dict[str, Any]:
    raw = record.get("raw") if isinstance(record.get("raw"), dict) else {}

    number = first_non_empty(
        record.get("number"),
        record.get("opp_num"),
        record.get("oppNum"),
        raw.get("number"),
        raw.get("oppNum"),
    )
    record_id = first_non_empty(
        record.get("id"),
        raw.get("id"),
        number,
    )

    title = first_non_empty(record.get("title"), raw.get("title"), raw.get("oppTitle"))
    agency = first_non_empty(record.get("agency"), raw.get("agency"), raw.get("agencyName"), raw.get("agencyCode"))
    status = first_non_empty(record.get("status"), raw.get("oppStatus"), "unknown")
    open_date = first_non_empty(record.get("open_date"), raw.get("openDate"))
    close_date = first_non_empty(record.get("close_date"), raw.get("closeDate"))
    doc_type = first_non_empty(record.get("doc_type"), raw.get("docType"), "")

    synopsis = first_non_empty(
        record.get("synopsis"),
        raw.get("synopsis"),
        raw.get("description"),
        record.get("description"),
    )
    synopsis = strip_html(synopsis)

    url = first_non_empty(
        record.get("url"),
        raw.get("opportunityUrl"),
    )

    award_ceiling = to_float(
        first_non_empty(record.get("award_ceiling_usd"), raw.get("awardCeiling"), raw.get("award_ceiling"))
    )
    award_floor = to_float(
        first_non_empty(record.get("award_floor_usd"), raw.get("awardFloor"), raw.get("award_floor"))
    )
    total_funding = to_float(
        first_non_empty(record.get("total_funding_usd"), raw.get("estimatedTotalProgramFunding"), raw.get("total_funding"))
    )
    expected_awards = to_int(
        first_non_empty(record.get("expected_awards"), raw.get("expectedAwards"), raw.get("expectedNumberOfAwards"))
    )

    cfda_list = []
    raw_cfda = raw.get("cfdaList")
    if isinstance(raw_cfda, list):
        cfda_list = [str(item).strip() for item in raw_cfda if str(item).strip()]

    return {
        "source_channel": source_channel,
        "source_file": str(source_file),
        "source": first_non_empty(record.get("source"), source_channel),
        "id": record_id,
        "number": number,
        "title": title,
        "agency": agency,
        "status": status,
        "open_date": open_date,
        "close_date": close_date,
        "doc_type": doc_type,
        "url": url,
        "synopsis": synopsis,
        "award_ceiling_usd": award_ceiling,
        "award_floor_usd": award_floor,
        "total_funding_usd": total_funding,
        "expected_awards": expected_awards,
        "cfda_list": cfda_list,
    }


def ingest_records(source_files: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for path in source_files:
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue

        channel = "unknown"
        raw_records: list[dict[str, Any]] = []

        if path.name == "ranked.json":
            channel = "opportunities_ranked"
            rows = payload.get("records", [])
            if isinstance(rows, list):
                raw_records = [row for row in rows if isinstance(row, dict)]
        elif path.name.startswith("harvest_"):
            channel = "opportunities_harvest"
            rows = payload.get("records", [])
            if isinstance(rows, list):
                raw_records = [row for row in rows if isinstance(row, dict)]
        elif path.name == "grants_ranked_v2.json":
            channel = "grants_ranked_v2"
            rows = payload.get("ranked", [])
            if isinstance(rows, list):
                raw_records = [row for row in rows if isinstance(row, dict)]

        for row in raw_records:
            normalized = normalize_record(row, channel, path)
            if normalized.get("title"):
                records.append(normalized)

    return records


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    def _key(row: dict[str, Any]) -> str:
        number = normalize_text(row.get("number"))
        record_id = normalize_text(row.get("id"))
        title = normalize_text(row.get("title"))
        close_date = normalize_text(row.get("close_date"))
        if number:
            return f"number::{number}"
        if record_id:
            return f"id::{record_id}"
        return f"title::{title}::{close_date}"

    for row in records:
        k = _key(row)
        if k not in merged:
            row_copy = dict(row)
            row_copy["source_channels"] = [str(row.get("source_channel") or "")]
            row_copy["source_files"] = [str(row.get("source_file") or "")]
            merged[k] = row_copy
            continue

        target = merged[k]
        for field in (
            "number",
            "id",
            "title",
            "agency",
            "status",
            "open_date",
            "close_date",
            "doc_type",
            "url",
            "synopsis",
            "award_ceiling_usd",
            "award_floor_usd",
            "total_funding_usd",
            "expected_awards",
        ):
            current = target.get(field)
            incoming = row.get(field)
            if (current is None or current == "") and incoming not in (None, ""):
                target[field] = incoming

        source_channel = str(row.get("source_channel") or "")
        if source_channel and source_channel not in target["source_channels"]:
            target["source_channels"].append(source_channel)

        source_file = str(row.get("source_file") or "")
        if source_file and source_file not in target["source_files"]:
            target["source_files"].append(source_file)

        cfda_existing = target.get("cfda_list", [])
        cfda_incoming = row.get("cfda_list", [])
        if not isinstance(cfda_existing, list):
            cfda_existing = []
        if not isinstance(cfda_incoming, list):
            cfda_incoming = []
        combined = []
        seen = set()
        for item in cfda_existing + cfda_incoming:
            token = str(item).strip()
            if token and token not in seen:
                seen.add(token)
                combined.append(token)
        target["cfda_list"] = combined

    return list(merged.values())


def keyword_score(blob: str, weights: dict[str, float], multiplier: float) -> tuple[float, list[str], float]:
    hits: list[str] = []
    weight_sum = 0.0
    norm_blob = normalize_text(blob)

    for term, weight in weights.items():
        if term in norm_blob:
            hits.append(term)
            weight_sum += float(weight)

    score = min(100.0, weight_sum * multiplier)
    return round(score, 4), hits, round(weight_sum, 4)


def compute_healthcare_score(row: dict[str, Any]) -> tuple[float, list[str], dict[str, float]]:
    title = str(row.get("title") or "")
    agency = str(row.get("agency") or "")
    synopsis = str(row.get("synopsis") or "")
    number = str(row.get("number") or "")

    blob = " ".join([title, agency, synopsis, number])
    key_score, keyword_hits, keyword_weight_sum = keyword_score(blob, HEALTHCARE_KEYWORD_WEIGHTS, multiplier=2.7)

    agency_bonus = 0.0
    agency_blob = normalize_text(agency)
    for marker, bonus in AGENCY_HEALTH_BONUS.items():
        if marker in agency_blob:
            agency_bonus = max(agency_bonus, float(bonus))

    cfda_bonus = 0.0
    cfda_list = row.get("cfda_list", [])
    if isinstance(cfda_list, list):
        for cfda in cfda_list:
            token = str(cfda).strip()
            if token.startswith("93."):
                cfda_bonus = 18.0
                break

    total = min(100.0, key_score + agency_bonus + cfda_bonus)

    components = {
        "keyword_score": round(key_score, 4),
        "keyword_weight_sum": keyword_weight_sum,
        "agency_bonus": round(agency_bonus, 4),
        "cfda_bonus": round(cfda_bonus, 4),
    }
    return round(total, 4), keyword_hits, components


def compute_urgency_score(days: int | None) -> float:
    if days is None:
        return 0.0
    if days < 0:
        return 0.0
    if days <= 3:
        return 100.0
    if days <= 7:
        return 90.0
    if days <= 14:
        return 75.0
    if days <= 30:
        return 55.0
    if days <= 45:
        return 40.0
    if days <= 60:
        return 25.0
    return 10.0


def compute_scientific_score(row: dict[str, Any]) -> tuple[float, list[str], float]:
    blob = " ".join([
        str(row.get("title") or ""),
        str(row.get("synopsis") or ""),
        str(row.get("number") or ""),
    ])
    return keyword_score(blob, SCIENCE_KEYWORD_WEIGHTS, multiplier=3.3)


def compute_funding_score(row: dict[str, Any]) -> float:
    ceiling = row.get("award_ceiling_usd")
    total = row.get("total_funding_usd")
    awards = row.get("expected_awards")

    principal = ceiling if isinstance(ceiling, (int, float)) and ceiling > 0 else total
    if not isinstance(principal, (int, float)) or principal <= 0:
        base = 20.0
    else:
        base = min(100.0, 20.0 + (math.log10(float(principal) + 1.0) * 16.0))

    if isinstance(awards, int) and awards > 0:
        base += min(15.0, 35.0 / float(awards))

    return round(min(100.0, base), 4)


def compute_completeness_score(row: dict[str, Any], close_days: int | None) -> float:
    score = 0.0
    status = normalize_text(row.get("status"))
    synopsis = str(row.get("synopsis") or "")

    if status in {"posted", "open", "active", "forecasted"}:
        score += 35.0
    if close_days is not None:
        score += 35.0
    if str(row.get("url") or "").strip():
        score += 15.0
    if len(synopsis) >= 40:
        score += 15.0

    return round(min(100.0, score), 4)


def action_label(days: int | None) -> str:
    if days is None:
        return "MANUAL_REVIEW"
    if days < 0:
        return "CLOSED_OR_EXPIRED"
    if days <= 7:
        return "URGENT_REVIEW"
    if days <= 14:
        return "EXPEDITED_REVIEW"
    if days <= 30:
        return "ACTIVE_REVIEW"
    return "WATCHLIST"


def source_identity_sha256(row: dict[str, Any]) -> str:
    payload = {
        "number": row.get("number"),
        "url": row.get("url"),
        "open_date": row.get("open_date"),
        "close_date": row.get("close_date"),
        "source_channels": row.get("source_channels", []),
        "source_files": row.get("source_files", []),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def build_engine(
    records: list[dict[str, Any]],
    expiring_days: int,
    min_healthcare_score: float,
    top_n: int,
    include_forecasted: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scored: list[dict[str, Any]] = []

    for row in records:
        close_days = days_to_close(row.get("close_date"))
        status = normalize_text(row.get("status"))

        if close_days is None:
            continue
        if close_days < 0:
            continue
        if close_days > expiring_days:
            continue
        if (not include_forecasted) and status == "forecasted":
            continue

        healthcare_score, healthcare_hits, healthcare_components = compute_healthcare_score(row)
        if healthcare_score < float(min_healthcare_score):
            continue

        urgency_score = compute_urgency_score(close_days)
        scientific_score, scientific_hits, scientific_weight_sum = compute_scientific_score(row)
        funding_score = compute_funding_score(row)
        completeness_score = compute_completeness_score(row, close_days)

        composite_score = (
            (0.40 * healthcare_score)
            + (0.30 * urgency_score)
            + (0.15 * scientific_score)
            + (0.10 * funding_score)
            + (0.05 * completeness_score)
        )

        if status == "forecasted":
            composite_score *= 0.85

        scored.append(
            {
                "id": row.get("id"),
                "number": row.get("number"),
                "title": row.get("title"),
                "agency": row.get("agency"),
                "status": row.get("status"),
                "open_date": row.get("open_date"),
                "close_date": row.get("close_date"),
                "days_to_close": close_days,
                "doc_type": row.get("doc_type"),
                "url": row.get("url"),
                "action": action_label(close_days),
                "eligibility_status": "UNVERIFIED_REQUIRES_OFFICIAL_SOURCE_REVIEW",
                "deadline_verified_utc": None,
                "submission_authorized": False,
                "abstention_reason": (
                    "Official-source eligibility, current deadline, amendments, "
                    "submission route, and organization authority are not verified."
                ),
                "source_sha256": source_identity_sha256(row),
                "scores": {
                    "composite": round(composite_score, 4),
                    "healthcare": healthcare_score,
                    "urgency": urgency_score,
                    "scientific": scientific_score,
                    "funding": funding_score,
                    "completeness": completeness_score,
                },
                "healthcare_components": healthcare_components,
                "healthcare_keyword_hits": healthcare_hits[:18],
                "scientific_keyword_hits": scientific_hits[:18],
                "scientific_keyword_weight_sum": scientific_weight_sum,
                "funding": {
                    "award_ceiling_usd": row.get("award_ceiling_usd"),
                    "award_floor_usd": row.get("award_floor_usd"),
                    "total_funding_usd": row.get("total_funding_usd"),
                    "expected_awards": row.get("expected_awards"),
                },
                "cfda_list": row.get("cfda_list", []),
                "source_channels": row.get("source_channels", []),
                "source_files": row.get("source_files", []),
            }
        )

    scored.sort(
        key=lambda r: (
            float(r.get("scores", {}).get("composite", 0.0)),
            -int(r.get("days_to_close", 999999)),
            str(r.get("title") or ""),
        ),
        reverse=True,
    )

    selected = scored[: max(int(top_n), 1)]

    agency_counts = Counter(str(row.get("agency") or "") for row in selected if str(row.get("agency") or "").strip())
    action_counts = Counter(str(row.get("action") or "") for row in selected if str(row.get("action") or "").strip())

    close_windows = {
        "within_3_days": sum(1 for row in selected if int(row.get("days_to_close", 999999)) <= 3),
        "within_7_days": sum(1 for row in selected if int(row.get("days_to_close", 999999)) <= 7),
        "within_14_days": sum(1 for row in selected if int(row.get("days_to_close", 999999)) <= 14),
        "within_30_days": sum(1 for row in selected if int(row.get("days_to_close", 999999)) <= 30),
        "within_45_days": sum(1 for row in selected if int(row.get("days_to_close", 999999)) <= 45),
        "within_60_days": sum(1 for row in selected if int(row.get("days_to_close", 999999)) <= 60),
    }

    metrics = {
        "n_scanned": int(len(records)),
        "n_scored": int(len(scored)),
        "n_selected": int(len(selected)),
        "close_window_counts": close_windows,
        "action_counts": dict(action_counts),
        "top_agencies": [{"agency": agency, "count": count} for agency, count in agency_counts.most_common(12)],
    }

    return selected, metrics


def csv_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(records, start=1):
        scores = row.get("scores", {}) if isinstance(row.get("scores"), dict) else {}
        funding = row.get("funding", {}) if isinstance(row.get("funding"), dict) else {}
        out.append(
            {
                "rank": idx,
                "composite_score": scores.get("composite"),
                "healthcare_score": scores.get("healthcare"),
                "urgency_score": scores.get("urgency"),
                "scientific_score": scores.get("scientific"),
                "funding_score": scores.get("funding"),
                "completeness_score": scores.get("completeness"),
                "days_to_close": row.get("days_to_close"),
                "action": row.get("action"),
                "eligibility_status": row.get("eligibility_status"),
                "deadline_verified_utc": row.get("deadline_verified_utc"),
                "submission_authorized": row.get("submission_authorized"),
                "abstention_reason": row.get("abstention_reason"),
                "source_sha256": row.get("source_sha256"),
                "number": row.get("number"),
                "title": row.get("title"),
                "agency": row.get("agency"),
                "status": row.get("status"),
                "open_date": row.get("open_date"),
                "close_date": row.get("close_date"),
                "award_ceiling_usd": funding.get("award_ceiling_usd"),
                "total_funding_usd": funding.get("total_funding_usd"),
                "expected_awards": funding.get("expected_awards"),
                "cfda_list": "|".join(str(x) for x in row.get("cfda_list", []) if str(x).strip()),
                "healthcare_keyword_hits": "|".join(str(x) for x in row.get("healthcare_keyword_hits", []) if str(x).strip()),
                "scientific_keyword_hits": "|".join(str(x) for x in row.get("scientific_keyword_hits", []) if str(x).strip()),
                "source_channels": "|".join(str(x) for x in row.get("source_channels", []) if str(x).strip()),
                "url": row.get("url"),
            }
        )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(
    generated_utc: str,
    scope: dict[str, Any],
    metrics: dict[str, Any],
    records: list[dict[str, Any]],
    evidence_paths: list[str],
) -> str:
    lines: list[str] = []
    lines.append("# Healthcare Grants Engine Report")
    lines.append("")
    lines.append(f"- Generated UTC: {generated_utc}")
    lines.append(f"- Scope: expiring_within_days={scope.get('expiring_within_days')}, min_healthcare_score={scope.get('min_healthcare_score')}, top_n={scope.get('top_n')}")
    lines.append(f"- Scanned records: {metrics.get('n_scanned', 0)}")
    lines.append(f"- Healthcare-scored records: {metrics.get('n_scored', 0)}")
    lines.append(f"- Selected records: {metrics.get('n_selected', 0)}")
    lines.append("")

    lines.append("## Deadline Windows")
    close_windows = metrics.get("close_window_counts", {}) if isinstance(metrics.get("close_window_counts"), dict) else {}
    for key in ("within_3_days", "within_7_days", "within_14_days", "within_30_days", "within_45_days", "within_60_days"):
        lines.append(f"- {key}: {close_windows.get(key, 0)}")
    lines.append("")

    lines.append("## Action Mix")
    action_counts = metrics.get("action_counts", {}) if isinstance(metrics.get("action_counts"), dict) else {}
    if action_counts:
        for action, count in action_counts.items():
            lines.append(f"- {action}: {count}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Top Agencies")
    top_agencies = metrics.get("top_agencies", []) if isinstance(metrics.get("top_agencies"), list) else []
    if top_agencies:
        for row in top_agencies:
            if not isinstance(row, dict):
                continue
            lines.append(f"- {row.get('agency')}: {row.get('count')}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Top Expiring Healthcare Grants")
    lines.append("| Rank | Days | Score | Action | Number | Agency | Title |")
    lines.append("|---|---:|---:|---|---|---|---|")
    for idx, row in enumerate(records[:25], start=1):
        score = (row.get("scores") or {}).get("composite", 0)
        lines.append(
            "| "
            f"{idx} | {row.get('days_to_close')} | {float(score):.2f} | {row.get('action')} | "
            f"{row.get('number')} | {row.get('agency')} | {row.get('title')} |"
        )
    lines.append("")

    lines.append("## Evidence Paths")
    for path in evidence_paths:
        lines.append(f"- {path}")

    return "\n".join(lines)


def run(
    expiring_days: int,
    min_healthcare_score: float,
    top_n: int,
    include_forecasted: bool,
) -> dict[str, Any]:
    source_files = collect_source_files()
    if not source_files:
        raise RuntimeError("No source files found. Expected ranked/harvest/grants ranked artifacts.")

    raw_records = ingest_records(source_files)
    deduped_records = dedupe_records(raw_records)

    selected, metrics = build_engine(
        deduped_records,
        expiring_days=expiring_days,
        min_healthcare_score=min_healthcare_score,
        top_n=top_n,
        include_forecasted=include_forecasted,
    )

    generated_utc = now_utc_iso()
    tag = now_tag()
    scope = {
        "expiring_within_days": int(expiring_days),
        "min_healthcare_score": float(min_healthcare_score),
        "top_n": int(top_n),
        "include_forecasted": bool(include_forecasted),
    }

    payload = {
        "schema": "healthcare_grants_engine_v2",
        "generated_utc": generated_utc,
        "scope": scope,
        "evidence": {
            "source_files": [str(p) for p in source_files],
            "engine_script": str(ROOT / "code" / "ops" / "run_healthcare_grants_engine.py"),
        },
        "metrics": metrics,
        "records": selected,
    }

    version_json = OUT_DIR / f"healthcare_grants_engine_{tag}.json"
    latest_json = OUT_DIR / "healthcare_grants_engine_latest.json"

    csv_data = csv_rows(selected)
    version_csv = OUT_DIR / f"healthcare_grants_engine_{tag}.csv"
    latest_csv = OUT_DIR / "healthcare_grants_engine_latest.csv"

    report_md = build_markdown(
        generated_utc=generated_utc,
        scope=scope,
        metrics=metrics,
        records=selected,
        evidence_paths=[str(p) for p in source_files],
    )
    version_md = OUT_DIR / f"healthcare_grants_engine_{tag}.md"
    latest_md = OUT_DIR / "healthcare_grants_engine_latest.md"

    write_json(version_json, payload)
    write_json(latest_json, payload)

    write_csv(version_csv, csv_data)
    write_csv(latest_csv, csv_data)

    write_text(version_md, report_md)
    write_text(latest_md, report_md)

    heartbeat = {
        "generated_utc": generated_utc,
        "status": "ok",
        "reason": "pipeline_complete",
        "scope": scope,
        "metrics": {
            "n_scanned": metrics.get("n_scanned", 0),
            "n_scored": metrics.get("n_scored", 0),
            "n_selected": metrics.get("n_selected", 0),
        },
        "artifacts": {
            "json": str(version_json),
            "json_latest": str(latest_json),
            "csv": str(version_csv),
            "csv_latest": str(latest_csv),
            "markdown": str(version_md),
            "markdown_latest": str(latest_md),
        },
        "evidence_paths": [str(p) for p in source_files],
    }

    heartbeat_path = OUT_DIR / "healthcare_grants_engine_heartbeat_latest.json"
    write_json(heartbeat_path, heartbeat)

    result = {
        "generated_utc": generated_utc,
        "scope": scope,
        "metrics": metrics,
        "artifacts": heartbeat["artifacts"],
        "heartbeat": str(heartbeat_path),
    }
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a healthcare grants expiring-soon intelligence pack with quantitative scoring."
    )
    parser.add_argument("--expiring-days", type=int, default=45, help="Only include grants closing within this many days.")
    parser.add_argument("--min-healthcare-score", type=float, default=35.0, help="Minimum healthcare relevance score (0-100).")
    parser.add_argument("--top-n", type=int, default=40, help="Maximum selected records in output artifacts.")
    parser.add_argument("--include-forecasted", action="store_true", help="Include forecasted opportunities in the final ranked list.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run(
        expiring_days=max(int(args.expiring_days), 1),
        min_healthcare_score=max(float(args.min_healthcare_score), 0.0),
        top_n=max(int(args.top_n), 1),
        include_forecasted=bool(args.include_forecasted),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
