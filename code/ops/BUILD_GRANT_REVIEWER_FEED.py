from __future__ import annotations

import hashlib
import json
import re
import tempfile
from copy import deepcopy
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
CURATION = ROOT / "config" / "grant_reviewer_curation_v1.json"
RANKED = ROOT / "out" / "opportunities" / "ranked.json"
HARVESTS = ROOT / "out" / "opportunities"
QUEUE = ROOT / "out" / "grants" / "_queue" / "index.json"
LEDGER = ROOT / "out" / "ops" / "grants_live_submission_ledger_latest.json"
READINESS = ROOT / "out" / "ops" / "grant_dashboard_status_feed_latest.json"
REPRO_TEMPLATE = ROOT / "config" / "falcon_independent_reproduction_receipt_template_v1.json"
OUT_OPS = ROOT / "out" / "ops" / "grant_reviewer_feed_latest.json"
OUT_DASHBOARD = ROOT / "dashboard" / "data" / "grant_reviewer_feed.json"

FEED_SCHEMA = "grant_reviewer_feed_v2"
CURATION_SCHEMA = "lumencore.grant_reviewer_curation.v1"
DEFAULT_TTL_HOURS = 24.0
ZERO_RECORD_STATUS = "ZERO_RECORDS_CAUSE_UNVERIFIED"
RECORDS_PRESENT_STATUS = "HARVESTED_RECORDS_PRESENT"


def _read_required_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required {label} source is missing: {path.relative_to(ROOT)}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Required {label} source is unreadable: {path.relative_to(ROOT)}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"Required {label} source must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: dict[str, Any]) -> str:
    rendered = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _latest_harvest() -> Path:
    candidates = sorted(HARVESTS.glob("harvest_*.json"), reverse=True)
    if not candidates:
        raise FileNotFoundError("No required opportunity harvest snapshot was found")
    return candidates[0]


def _number(value: Any) -> float | None:
    try:
        rendered = str(value).strip().replace(",", "")
        if not rendered or rendered.lower() in {"none", "null", "n/a"}:
            return None
        return float(rendered)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> tuple[datetime | None, bool]:
    raw = str(value or "").strip()
    if not raw:
        return None, False
    if re.fullmatch(r"\d{8}T\d{6}Z", raw):
        return datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc), False
    for date_format in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            parsed_date = datetime.strptime(raw, date_format).date()
            return datetime.combine(parsed_date, time.min, tzinfo=timezone.utc), True
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None, False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc), False


def _iso_utc(value: Any) -> str | None:
    parsed, _ = _parse_datetime(value)
    if parsed is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _age_hours(value: Any, now: datetime) -> float | None:
    parsed, _ = _parse_datetime(value)
    if parsed is None:
        return None
    return round(max((now - parsed).total_seconds() / 3600.0, 0.0), 3)


def _freshness_status(value: Any, now: datetime, ttl_hours: float) -> tuple[str, float | None]:
    age = _age_hours(value, now)
    if age is None:
        return "UNDATED_REVERIFY_REQUIRED", None
    if age > ttl_hours:
        return "STALE_REVERIFY_REQUIRED", age
    return "CURRENT_WITHIN_TTL", age


def _source_timestamp(payload: dict[str, Any]) -> str | None:
    for key in ("generated_utc", "harvested_utc", "updated_utc", "timestamp_utc", "verified_utc"):
        if payload.get(key):
            return _iso_utc(payload[key])
    return None


def _is_https_url(value: Any) -> bool:
    parsed = urlparse(str(value or ""))
    return parsed.scheme == "https" and bool(parsed.netloc)


def _validate_curation(curation: dict[str, Any]) -> None:
    if curation.get("schema") != CURATION_SCHEMA:
        raise ValueError(f"Unsupported curation schema: {curation.get('schema')!r}")
    ttl = _number(curation.get("reviewer_feed_ttl_hours"))
    if ttl is None or ttl <= 0:
        raise ValueError("Curation reviewer_feed_ttl_hours must be positive")
    if _iso_utc(curation.get("verified_utc")) is None:
        raise ValueError("Curation verified_utc must be a valid timestamp")

    candidates = curation.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Curation must contain at least one candidate")
    candidate_ids: set[str] = set()
    opportunity_numbers: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise TypeError("Every curated candidate must be a JSON object")
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        number = str(candidate.get("opportunity_number") or "").strip()
        if not candidate_id or candidate_id in candidate_ids:
            raise ValueError(f"Missing or duplicate candidate_id: {candidate_id!r}")
        if not number or number in opportunity_numbers:
            raise ValueError(f"Missing or duplicate opportunity_number: {number!r}")
        candidate_ids.add(candidate_id)
        opportunity_numbers.add(number)
        if not _is_https_url(candidate.get("source_url")):
            raise ValueError(f"Candidate {candidate_id} requires an HTTPS source_url")
        verification = candidate.get("source_verification")
        if not isinstance(verification, dict):
            raise ValueError(f"Candidate {candidate_id} requires source_verification")
        if _iso_utc(verification.get("verified_utc")) is None:
            raise ValueError(f"Candidate {candidate_id} requires a valid source verification timestamp")
        if not str(verification.get("status") or "").strip():
            raise ValueError(f"Candidate {candidate_id} requires a source authority status")
        if not _is_https_url(verification.get("official_update_url")):
            raise ValueError(f"Candidate {candidate_id} requires an HTTPS official_update_url")

    allowlist = curation.get("curated_grants_gov_ids")
    if not isinstance(allowlist, list) or not all(str(item).strip() for item in allowlist):
        raise ValueError("Curation requires a nonempty Grants.gov allowlist")
    if len(allowlist) != len(set(map(str, allowlist))):
        raise ValueError("Curation Grants.gov allowlist contains duplicates")


def _deadline_controls(candidate: dict[str, Any], now: datetime) -> dict[str, Any]:
    start_raw = candidate.get("open_date") or candidate.get("published_date")
    close_raw = candidate.get("close_date")
    start, start_date_only = _parse_datetime(start_raw)
    close, close_date_only = _parse_datetime(close_raw)

    if start is not None:
        starts_later = start.date() > now.date() if start_date_only else start > now
        if starts_later:
            return {
                "deadline_state": "NOT_OPEN_BY_PUBLISHED_DATES",
                "hours_to_published_deadline": None,
                "published_window_actionable": False,
            }
    if close is None:
        return {
            "deadline_state": "DEADLINE_UNVERIFIED",
            "hours_to_published_deadline": None,
            "published_window_actionable": False,
        }
    if close_date_only:
        if close.date() < now.date():
            return {
                "deadline_state": "PUBLISHED_DEADLINE_PASSED_REVERIFY",
                "hours_to_published_deadline": None,
                "published_window_actionable": False,
            }
        return {
            "deadline_state": "DATE_ONLY_TIME_REVERIFY",
            "hours_to_published_deadline": None,
            "published_window_actionable": True,
        }
    hours = round((close - now).total_seconds() / 3600.0, 3)
    if hours <= 0:
        return {
            "deadline_state": "PUBLISHED_DEADLINE_PASSED_REVERIFY",
            "hours_to_published_deadline": hours,
            "published_window_actionable": False,
        }
    return {
        "deadline_state": "OPEN_BY_PUBLISHED_DATES",
        "hours_to_published_deadline": hours,
        "published_window_actionable": True,
    }


def _receipt_summary(ledger: dict[str, Any]) -> dict[str, Any]:
    records = [row for row in ledger.get("records", []) if isinstance(row, dict)]
    statuses = [str(row.get("status") or "").strip().lower() for row in records]
    successful = sum(
        1
        for status in statuses
        if (status.startswith("submitted") or status == "received_by_agency")
        and "rejected" not in status
    )
    return {
        "successful_submission_or_received": successful,
        "agency_tracking_assigned": sum("tracking_assigned" in status for status in statuses),
        "agency_received": sum(status == "received_by_agency" for status in statuses),
        "rejected_with_errors": sum("rejected" in status for status in statuses),
        "award_receipts": sum(status in {"awarded", "award_received"} for status in statuses),
        "receipt_boundary": (
            "Submission, tracking, and agency-received receipts are not awards, technical validation, "
            "eligibility decisions, selections, or endorsements."
        ),
    }


def _curated_candidates(
    curation: dict[str, Any], now: datetime, ttl_hours: float
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_candidate in curation["candidates"]:
        candidate = deepcopy(source_candidate)
        verification = candidate.pop("source_verification")
        authority_status = str(verification["status"])
        source_freshness, source_age = _freshness_status(
            verification["verified_utc"], now, ttl_hours
        )
        candidate.update(
            {
                "source_authority_status": authority_status,
                "source_verified_utc": _iso_utc(verification["verified_utc"]),
                "source_age_hours": source_age,
                "source_freshness_status": source_freshness,
                "source_recheck_required": (
                    "RECHECK_REQUIRED" in authority_status or source_freshness != "CURRENT_WITHIN_TTL"
                ),
                "source_authority_boundary": verification.get("authority_boundary"),
                "official_update_url": verification.get("official_update_url"),
                "published_deadline_text": verification.get("deadline_text"),
                **_deadline_controls(candidate, now),
            }
        )
        rows.append(candidate)
    return rows


def _discovery_records(
    ranked: dict[str, Any], allowlist: list[str], now: datetime, ttl_hours: float
) -> list[dict[str, Any]]:
    records_by_number: dict[str, dict[str, Any]] = {}
    for candidate in ranked.get("records", []):
        if not isinstance(candidate, dict):
            continue
        number = str(candidate.get("number") or candidate.get("id") or "").strip()
        if number and number not in records_by_number:
            records_by_number[number] = candidate

    source_verified_utc = _source_timestamp(ranked)
    source_freshness, source_age = _freshness_status(source_verified_utc, now, ttl_hours)
    rows: list[dict[str, Any]] = []
    for opportunity_number in allowlist:
        record = records_by_number.get(str(opportunity_number))
        if not record:
            continue
        raw = record.get("raw") if isinstance(record.get("raw"), dict) else {}
        source_url = record.get("url")
        if not _is_https_url(source_url):
            continue
        row = {
            "candidate_id": f"{record.get('source', 'source')}:{record.get('number') or record.get('id')}",
            "source": record.get("source"),
            "opportunity_number": record.get("number") or record.get("id"),
            "title": record.get("title"),
            "agency": record.get("agency"),
            "open_date": record.get("open_date"),
            "close_date": record.get("close_date"),
            "source_url": source_url,
            "official_update_url": source_url,
            "notice_award_floor_usd": _number(raw.get("awardFloor")),
            "notice_award_ceiling_usd": _number(raw.get("awardCeiling")),
            "source_notice_status": raw.get("oppStatus"),
            "discovery_match_score": round(float(record.get("_fit_score") or 0.0), 4),
            "keyword_matches": [str(value) for value in record.get("_keyword_matches", [])[:8]],
            "eligibility_status": "UNVERIFIED",
            "submission_status": "DISCOVERY_ONLY",
            "source_authority_status": "OFFICIAL_DISCOVERY_SNAPSHOT_NOTICE_RECHECK_REQUIRED",
            "source_verified_utc": source_verified_utc,
            "source_age_hours": source_age,
            "source_freshness_status": source_freshness,
            "source_recheck_required": True,
            "source_authority_boundary": (
                "This record was harvested from Grants.gov for discovery. The complete current notice "
                "and linked agency instructions control eligibility and submission."
            ),
            "next_gate": (
                "Read the complete current notice and document applicant, team, budget, cost-share, "
                "and submission-route eligibility."
            ),
            "claim_boundary": (
                "Keyword discovery is not a qualification, eligibility, responsiveness, "
                "selection, or award prediction."
            ),
        }
        row.update(_deadline_controls(row, now))
        rows.append(row)
    return rows


def _source_health(harvest: dict[str, Any], now: datetime, ttl_hours: float) -> dict[str, Any]:
    harvested_utc = _source_timestamp(harvest)
    freshness, age = _freshness_status(harvested_utc, now, ttl_hours)
    totals = harvest.get("totals") if isinstance(harvest.get("totals"), dict) else {}
    result: dict[str, Any] = {}
    for key in ("grants_gov", "sam_gov", "sbir_gov"):
        count = int(totals.get(key) or 0)
        result[key] = {
            "records": count,
            "status": RECORDS_PRESENT_STATUS if count > 0 else ZERO_RECORD_STATUS,
            "harvested_utc": harvested_utc,
            "source_age_hours": age,
            "source_freshness_status": freshness,
            "boundary": (
                "A zero-record result proves only that this snapshot contains zero records; "
                "it does not establish outage, maintenance, rate limiting, or absence of opportunities."
                if count == 0
                else "Record count describes this bounded harvest snapshot, not all current opportunities."
            ),
        }
    return result


def _provenance_descriptor(
    path: Path,
    payload: dict[str, Any],
    now: datetime,
    ttl_hours: float,
    timestamp: Any = None,
) -> dict[str, Any]:
    source_utc = _iso_utc(timestamp) if timestamp else _source_timestamp(payload)
    freshness, age = _freshness_status(source_utc, now, ttl_hours)
    return {
        "relative_path": path.relative_to(ROOT).as_posix(),
        "present": True,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "source_generated_utc": source_utc,
        "source_age_hours": age,
        "freshness_status": freshness,
    }


def _validate_public_feed(feed: dict[str, Any]) -> None:
    if feed.get("schema") != FEED_SCHEMA:
        raise ValueError("Reviewer feed schema mismatch")
    control_sha = str(feed.get("control_sha256") or "")
    unsigned = dict(feed)
    unsigned.pop("control_sha256", None)
    if control_sha != _canonical_sha256(unsigned):
        raise ValueError("Reviewer feed control hash mismatch")

    rendered = json.dumps(feed, ensure_ascii=True, sort_keys=True)
    lowered = rendered.lower()
    forbidden_fragments = (
        "submission_packet",
        "@gmail.com",
        "private_application",
        "tax_identifier",
        "api_key",
        "client_secret",
        "access_token",
        "c:\\\\",
        "e:\\\\",
    )
    for fragment in forbidden_fragments:
        if fragment in lowered:
            raise ValueError(f"Reviewer feed contains forbidden private fragment: {fragment}")
    if re.search(r"\b\d{2}-\d{7}\b", rendered):
        raise ValueError("Reviewer feed contains an EIN-shaped value")
    if re.search(r"\b\d{3}[-.) ]+\d{3}[-. ]+\d{4}\b", rendered):
        raise ValueError("Reviewer feed contains a phone-shaped value")
    if re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", rendered, re.IGNORECASE):
        raise ValueError("Reviewer feed contains an email-shaped value")
    if "agency_validated" in feed.get("summary", {}):
        raise ValueError("Receipt state must not be presented as agency validation")

    candidates = feed.get("discovered_opportunities")
    if not isinstance(candidates, list):
        raise TypeError("Reviewer feed candidates must be a list")
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id or candidate_id in seen:
            raise ValueError(f"Missing or duplicate reviewer candidate: {candidate_id!r}")
        seen.add(candidate_id)
        for key in ("source_url", "official_update_url"):
            if not _is_https_url(candidate.get(key)):
                raise ValueError(f"Candidate {candidate_id} has a non-HTTPS {key}")
        if candidate.get("deadline_state") == "PUBLISHED_DEADLINE_PASSED_REVERIFY" and candidate.get(
            "published_window_actionable"
        ):
            raise ValueError(f"Expired candidate {candidate_id} cannot be marked actionable")

    provenance = feed.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise ValueError("Reviewer feed provenance is missing")
    for descriptor in provenance.values():
        if not descriptor.get("present") or len(str(descriptor.get("sha256") or "")) != 64:
            raise ValueError("Reviewer feed provenance is incomplete")
        relative_path = str(descriptor.get("relative_path") or "")
        if not relative_path or Path(relative_path).is_absolute() or ":" in relative_path:
            raise ValueError("Reviewer feed provenance must use repository-relative paths")


def build_feed(generated_utc: str | None = None) -> dict[str, Any]:
    now, _ = _parse_datetime(generated_utc or datetime.now(timezone.utc).isoformat())
    if now is None:
        raise ValueError("generated_utc must be a valid timestamp")
    generated = now.isoformat().replace("+00:00", "Z")

    curation = _read_required_json(CURATION, "curation control")
    _validate_curation(curation)
    ranked = _read_required_json(RANKED, "ranked opportunity")
    queue = _read_required_json(QUEUE, "local grant queue")
    ledger = _read_required_json(LEDGER, "submission receipt ledger")
    readiness = _read_required_json(READINESS, "grant readiness")
    receipt = _read_required_json(REPRO_TEMPLATE, "independent reproduction template")
    harvest_path = _latest_harvest()
    harvest = _read_required_json(harvest_path, "opportunity harvest")

    ttl_hours = float(curation.get("reviewer_feed_ttl_hours") or DEFAULT_TTL_HOURS)
    candidates = _curated_candidates(curation, now, ttl_hours)
    candidates.extend(
        _discovery_records(
            ranked,
            [str(value) for value in curation["curated_grants_gov_ids"]],
            now,
            ttl_hours,
        )
    )
    priority = next(
        (candidate for candidate in candidates if candidate["opportunity_number"] == "DPA26BZ04-DV016"),
        None,
    )
    if priority is None:
        raise ValueError("Required FALCON priority candidate is absent from curation")

    expected = receipt.get("frozen_evidence", {}).get("expected_result", {})
    readiness_summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    queue_utc = _source_timestamp(queue)
    queue_freshness, queue_age = _freshness_status(queue_utc, now, ttl_hours)
    readiness_utc = _source_timestamp(readiness)
    readiness_freshness, readiness_age = _freshness_status(readiness_utc, now, ttl_hours)
    fresh_until = now.timestamp() + ttl_hours * 3600.0

    feed: dict[str, Any] = {
        "schema": FEED_SCHEMA,
        "generated_utc": generated,
        "posture": "REVIEWER_SAFE_STATIC_DISCOVERY_AND_RECEIPT_SNAPSHOT",
        "freshness": {
            "generated_utc": generated,
            "ttl_hours": ttl_hours,
            "fresh_until_utc": datetime.fromtimestamp(fresh_until, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "status_at_build": "CURRENT_WITHIN_TTL",
            "static_snapshot": True,
            "boundary": "After fresh_until_utc, deadlines, source state, and portal state require re-verification.",
        },
        "summary": {
            "local_dossiers_indexed": int(queue.get("n_total") or 0),
            "local_approved_artifacts_indexed": int(queue.get("n_approved") or 0),
            "local_artifact_snapshot_utc": queue_utc,
            "local_artifact_snapshot_age_hours": queue_age,
            "local_artifact_snapshot_freshness": queue_freshness,
            "portal_user_gates_snapshot": int(readiness_summary.get("portal_user_blockers") or 0),
            "local_blockers_snapshot": int(readiness_summary.get("local_blockers") or 0),
            "readiness_snapshot_utc": readiness_utc,
            "readiness_snapshot_age_hours": readiness_age,
            "readiness_snapshot_freshness": readiness_freshness,
            **_receipt_summary(ledger),
        },
        "independent_reproduction": {
            "status": "AWAITING_INDEPENDENT_RUNNER",
            "lane": receipt.get("evidence_lane_id"),
            "template_schema": receipt.get("schema"),
            "protocol_sha256": receipt.get("frozen_evidence", {}).get("protocol_sha256"),
            "trace_terminal_sha256": receipt.get("frozen_evidence", {}).get("trace_terminal_sha256"),
            "expected_status": expected.get("status"),
            "expected_score": f"{expected.get('correct_decisions')}/{expected.get('decision_count')}",
            "qualification_gate_passed": bool(expected.get("qualification_gate_passed")),
            "performance_promotion_allowed": bool(receipt.get("performance_promotion_allowed")),
            "reviewer_identity_filled": bool(receipt.get("reviewer", {}).get("name")),
            "next_gate": (
                "An independent reviewer must run the frozen packet, fill reviewer-controlled fields, "
                "and sign the receipt."
            ),
            "claim_boundary": receipt.get("claim_boundary"),
        },
        "priority_candidate": deepcopy(priority),
        "discovered_opportunities": candidates,
        "curation": {
            "control_schema": curation.get("schema"),
            "control_verified_utc": _iso_utc(curation.get("verified_utc")),
            "basis": (
                "Explicit source-checked DoD candidates with bounded local evidence gates, followed "
                "by a controlled Grants.gov discovery allowlist."
            ),
            "automated_keyword_matches_published": False,
            "complete_controlling_notice_review_required": True,
            "claim_boundary": curation.get("claim_boundary"),
        },
        "source_health": _source_health(harvest, now, ttl_hours),
        "provenance": {
            "curation_control": _provenance_descriptor(
                CURATION, curation, now, ttl_hours, curation.get("verified_utc")
            ),
            "ranked_opportunities": _provenance_descriptor(RANKED, ranked, now, ttl_hours),
            "opportunity_harvest": _provenance_descriptor(harvest_path, harvest, now, ttl_hours),
            "local_grant_queue": _provenance_descriptor(QUEUE, queue, now, ttl_hours),
            "readiness_snapshot": _provenance_descriptor(READINESS, readiness, now, ttl_hours),
            "submission_receipt_ledger": _provenance_descriptor(LEDGER, ledger, now, ttl_hours),
            "reproduction_template": _provenance_descriptor(
                REPRO_TEMPLATE, receipt, now, ttl_hours
            ),
        },
        "claim_boundaries": [
            "This is a static reviewer snapshot; it is not a live portal view.",
            "No discovered opportunity is labeled qualified until the complete controlling notice is reviewed.",
            "Local artifacts remain drafts unless an official submission or validation receipt proves otherwise.",
            "Submission, tracking, and agency-received receipts are not awards or technical validation.",
            "Independent reproduction of the FALCON null result cannot promote it to a performance pass.",
            "No private application-form values, tax data, address, phone, email, signature, or credential is published.",
        ],
    }
    feed["control_sha256"] = _canonical_sha256(feed)
    _validate_public_feed(feed)
    return feed


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(rendered)
            handle.flush()
            temporary = Path(handle.name)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main() -> int:
    feed = build_feed()
    for path in (OUT_OPS, OUT_DASHBOARD):
        _atomic_write_json(path, feed)
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
