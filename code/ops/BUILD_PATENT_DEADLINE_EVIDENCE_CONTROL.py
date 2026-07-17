from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
PRIVATE_DIR = ROOT / "out" / "private"

OUT_JSON = SPRINT_DIR / "PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json"
OUT_MD = SPRINT_DIR / "PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.md"
PRIVATE_OUT = PRIVATE_DIR / "patent_deadline_evidence_docket_2026-07-16.json"

OFFICIAL_SOURCES = [
    {
        "label": "USPTO incomplete or missing application information",
        "url": "https://www.uspto.gov/patents/apply/when-patent-applications-are-incomplete-or-missing-information",
        "verified_fact": (
            "An OPAP notice identifies missing or deficient application items, the reply period, "
            "and any additional fees. The notice itself controls the response task."
        ),
    },
    {
        "label": "USPTO nonprovisional utility filing guide",
        "url": "https://www.uspto.gov/patents/basics/apply/utility-patent",
        "verified_fact": (
            "A nonprovisional utility application requires a specification with claims, any "
            "necessary drawings, an oath or declaration, and prescribed filing, search, and "
            "examination fees. Missing fees can produce a notice and surcharge."
        ),
    },
    {
        "label": "USPTO Patent Center",
        "url": "https://www.uspto.gov/patents/apply/patent-center",
        "verified_fact": (
            "Registered users can view private submissions, track application progress, inspect "
            "correspondence and fee history, and respond to USPTO correspondence."
        ),
    },
    {
        "label": "USPTO Pro Se Assistance Program",
        "url": "https://www.uspto.gov/patents/basics/using-legal-services/pro-se-assistance-program",
        "verified_fact": (
            "The program provides procedural assistance to applicants filing without a registered "
            "patent attorney or agent, but it does not provide legal advice."
        ),
    },
    {
        "label": "USPTO Patent Pro Bono Program",
        "url": "https://www.uspto.gov/patents/basics/using-legal-services/pro-bono/patent-pro-bono-program",
        "verified_fact": (
            "The program routes financially under-resourced inventors and small businesses to "
            "regional programs that may match them with volunteer practitioners."
        ),
    },
    {
        "label": "WIPO PCT restoration of priority",
        "url": "https://www.wipo.int/en/web/pct-system/texts/restoration",
        "verified_fact": (
            "PCT priority restoration is limited, jurisdiction-dependent, and time-sensitive. "
            "Availability must not be assumed."
        ),
    },
]

REQUIRED_PATENT_CENTER_CAPTURE = [
    {
        "item": "Application data and current status",
        "why": "Verify the official filing date, application type, entity status, continuity data, and current status.",
    },
    {
        "item": "Filing Receipt",
        "why": "A payment acknowledgement is not the Filing Receipt and does not establish the complete official docket posture.",
    },
    {
        "item": "All outgoing correspondence",
        "why": "Identify every OPAP notice, Office Action, abandonment notice, or other communication and its mailing date.",
    },
    {
        "item": "Submitted document list",
        "why": "Verify that the official file contains the specification, claims, abstract, drawings, ADS, and oath or declaration as applicable.",
    },
    {
        "item": "Fee payment history",
        "why": "Verify filing, search, examination, surcharge, excess-claim, and any other assessed or outstanding fees.",
    },
    {
        "item": "Transaction history",
        "why": "Reconcile each submission, notice, response, and status change in chronological order.",
    },
]

CLAIM_BOUNDARY = (
    "This control classifies only the local evidence supplied to it. A payment acknowledgement "
    "proves receipt of the listed payment, not a granted filing date, complete application, "
    "verified claims, current pendency, patentability, freedom to operate, or absence of an "
    "outstanding notice. A filing anniversary is not, by itself, a U.S. prosecution response "
    "deadline. Foreign or PCT priority strategy can be separately time-sensitive and requires "
    "prompt review by a registered patent practitioner."
)

PUBLIC_PROHIBITED_MARKERS = (
    "application_number",
    "payment_received_date",
    "private_source_path",
    "source_sha256",
    "correspondence address",
    "payment transaction",
    "card /",
    "attorney docket",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def collect_evidence(role_paths: dict[str, list[Path]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    canonical_by_hash: dict[str, str] = {}
    for role in sorted(role_paths):
        for raw_path in role_paths[role]:
            path = raw_path.expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(path)
            fingerprint = sha256_file(path)
            duplicate_of = canonical_by_hash.get(fingerprint)
            if duplicate_of is None:
                canonical_by_hash[fingerprint] = str(path)
            records.append(
                {
                    "role": role,
                    "private_source_path": str(path),
                    "source_name": path.name,
                    "bytes": path.stat().st_size,
                    "source_sha256": fingerprint,
                    "duplicate_of_private_source_path": duplicate_of,
                    "canonical": duplicate_of is None,
                }
            )
    return records


def build_private_payload(
    *,
    records: list[dict[str, Any]],
    application_number: str | None,
    application_type: str | None,
    payment_received_date: str | None,
    basic_filing_fee_only_observed: bool,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    roles = {str(row["role"]) for row in records}
    unique_hashes = {str(row["source_sha256"]) for row in records}
    payment_acknowledgement_found = bool(
        roles.intersection({"payment_acknowledgement", "payment_receipt_screenshot"})
    )
    filing_receipt_found = "filing_receipt" in roles
    official_correspondence_found = "official_correspondence" in roles
    official_status_record_found = "official_status_record" in roles
    claims_record_found = "claims_record" in roles

    payload: dict[str, Any] = {
        "schema": "lumencore.patent_deadline_private_docket.v1",
        "generated_utc": generated_utc or now_utc(),
        "private_only": True,
        "application_number": application_number,
        "application_type": application_type,
        "payment_received_date": payment_received_date,
        "evidence": records,
        "summary": {
            "source_count": len(records),
            "unique_source_count": len(unique_hashes),
            "duplicate_source_count": len(records) - len(unique_hashes),
            "document_roles": sorted(roles),
            "payment_acknowledgement_found": payment_acknowledgement_found,
            "filing_receipt_found": filing_receipt_found,
            "official_correspondence_found": official_correspondence_found,
            "official_status_record_found": official_status_record_found,
            "claims_record_found": claims_record_found,
            "basic_filing_fee_only_observed": basic_filing_fee_only_observed,
        },
        "deadline_posture": {
            "us_prosecution_deadline": "UNVERIFIED_REQUIRES_NEWEST_OFFICIAL_NOTICE",
            "filing_anniversary": "NOT_A_US_PROSECUTION_RESPONSE_DEADLINE_BY_ITSELF",
            "foreign_pct_priority": "TIME_SENSITIVE_PRACTITIONER_REVIEW_REQUIRED_IF_FOREIGN_RIGHTS_DESIRED",
            "priority_restoration": "LIMITED_JURISDICTION_DEPENDENT_NOT_ASSUMED",
        },
        "required_patent_center_capture": REQUIRED_PATENT_CENTER_CAPTURE,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["private_docket_sha256"] = stable_sha256(payload)
    return payload


def build_public_payload(private_payload: dict[str, Any]) -> dict[str, Any]:
    private_summary = private_payload["summary"]
    filing_receipt_found = bool(private_summary["filing_receipt_found"])
    official_correspondence_found = bool(
        private_summary["official_correspondence_found"]
    )
    official_status_record_found = bool(
        private_summary["official_status_record_found"]
    )

    if (
        filing_receipt_found
        and official_correspondence_found
        and official_status_record_found
    ):
        status = "OFFICIAL_DOCKET_CAPTURED_PRACTITIONER_REVIEW_REQUIRED"
    elif private_summary["payment_acknowledgement_found"]:
        status = "PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED"
    else:
        status = "NO_OFFICIAL_DOCKET_EVIDENCE_CAPTURED"

    payload: dict[str, Any] = {
        "schema": "lumencore.patent_deadline_evidence_control.v1",
        "generated_utc": private_payload["generated_utc"],
        "status": status,
        "direct_answer": (
            "The local record proves a payment acknowledgement only. It does not prove a "
            "Filing Receipt, complete application, current status, verified claims, or an "
            "outstanding response deadline. The official Patent Center docket must be captured "
            "before any U.S. deadline claim. Foreign or PCT priority strategy is a separate, "
            "potentially time-sensitive counsel question."
        ),
        "public_evidence_summary": {
            "source_count": int(private_summary["source_count"]),
            "unique_source_count": int(private_summary["unique_source_count"]),
            "duplicate_source_count": int(private_summary["duplicate_source_count"]),
            "document_roles": list(private_summary["document_roles"]),
            "payment_acknowledgement_found": bool(
                private_summary["payment_acknowledgement_found"]
            ),
            "filing_receipt_found": filing_receipt_found,
            "official_correspondence_found": official_correspondence_found,
            "official_status_record_found": official_status_record_found,
            "claims_record_found": bool(private_summary["claims_record_found"]),
            "basic_filing_fee_only_observed": bool(
                private_summary["basic_filing_fee_only_observed"]
            ),
            "private_paths_published": False,
            "private_hashes_published": False,
            "application_identifier_published": False,
            "payment_identifier_published": False,
        },
        "deadline_posture": private_payload["deadline_posture"],
        "required_patent_center_capture": REQUIRED_PATENT_CENTER_CAPTURE,
        "official_sources": OFFICIAL_SOURCES,
        "human_action_gate": {
            "browser_navigation_performed_by_control": False,
            "patent_center_download_required": True,
            "registered_practitioner_review_required": True,
            "legal_filing_allowed_without_human": False,
            "fee_payment_allowed_without_human": False,
            "signature_allowed_without_human": False,
            "public_claim_expansion_allowed": False,
            "next_safe_action": (
                "After the user confirms the signed-in Patent Center application page is ready, "
                "download the Filing Receipt, all outgoing correspondence, submitted-document "
                "list, fee history, transaction history, and current status without filing or paying."
            ),
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {"json": rel(OUT_JSON), "markdown": rel(OUT_MD)},
    }
    payload["control_sha256"] = stable_sha256(payload)
    validate_public_redaction(payload, private_payload)
    return payload


def validate_public_redaction(
    public_payload: dict[str, Any], private_payload: dict[str, Any]
) -> None:
    rendered = json.dumps(public_payload, sort_keys=True)
    lowered = rendered.lower()
    for marker in PUBLIC_PROHIBITED_MARKERS:
        if marker in lowered:
            raise ValueError(f"Public patent control contains prohibited marker: {marker}")

    private_values: set[str] = set()
    for key in ("application_number", "payment_received_date"):
        value = private_payload.get(key)
        if isinstance(value, str) and value:
            private_values.add(value)
    for row in private_payload.get("evidence", []):
        for key in (
            "private_source_path",
            "source_name",
            "source_sha256",
            "duplicate_of_private_source_path",
        ):
            value = row.get(key)
            if isinstance(value, str) and value:
                private_values.add(value)
    leaked = [value for value in private_values if value in rendered]
    if leaked:
        raise ValueError("Public patent control leaked private evidence values")

    if re.search(r"(?i)card\s*/\s*\d{4}", rendered):
        raise ValueError("Public patent control leaked a payment-card suffix")


def render_markdown(payload: dict[str, Any]) -> str:
    evidence = payload["public_evidence_summary"]
    gate = payload["human_action_gate"]
    lines = [
        "# Patent Deadline Evidence Control - 2026-07-16",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Direct Answer",
        "",
        payload["direct_answer"],
        "",
        "## Evidence Boundary",
        "",
        f"- Local source records: `{evidence['source_count']}`",
        f"- Unique source records: `{evidence['unique_source_count']}`",
        f"- Exact duplicate records: `{evidence['duplicate_source_count']}`",
        f"- Payment acknowledgement found: `{str(evidence['payment_acknowledgement_found']).lower()}`",
        f"- Filing Receipt found: `{str(evidence['filing_receipt_found']).lower()}`",
        f"- Official correspondence found: `{str(evidence['official_correspondence_found']).lower()}`",
        f"- Official status record found: `{str(evidence['official_status_record_found']).lower()}`",
        f"- Claims verified in official file: `{str(evidence['claims_record_found']).lower()}`",
        f"- Basic filing fee only observed in local receipt: `{str(evidence['basic_filing_fee_only_observed']).lower()}`",
        f"- Private paths published: `{str(evidence['private_paths_published']).lower()}`",
        f"- Private hashes published: `{str(evidence['private_hashes_published']).lower()}`",
        f"- Application identifier published: `{str(evidence['application_identifier_published']).lower()}`",
        f"- Control SHA-256: `{payload['control_sha256']}`",
        "",
        "## Deadline Posture",
        "",
        f"- U.S. prosecution deadline: `{payload['deadline_posture']['us_prosecution_deadline']}`",
        f"- Filing anniversary: `{payload['deadline_posture']['filing_anniversary']}`",
        f"- Foreign or PCT priority: `{payload['deadline_posture']['foreign_pct_priority']}`",
        f"- Priority restoration: `{payload['deadline_posture']['priority_restoration']}`",
        "",
        "## Required Patent Center Capture",
        "",
    ]
    for index, item in enumerate(payload["required_patent_center_capture"], start=1):
        lines.append(f"{index}. **{item['item']}** - {item['why']}")

    lines.extend(
        [
            "",
            "## Human Gate",
            "",
            f"- Patent Center download required: `{str(gate['patent_center_download_required']).lower()}`",
            f"- Registered practitioner review required: `{str(gate['registered_practitioner_review_required']).lower()}`",
            f"- Legal filing without human: `{str(gate['legal_filing_allowed_without_human']).lower()}`",
            f"- Fee payment without human: `{str(gate['fee_payment_allowed_without_human']).lower()}`",
            f"- Signature without human: `{str(gate['signature_allowed_without_human']).lower()}`",
            f"- Browser navigation performed by this control: `{str(gate['browser_navigation_performed_by_control']).lower()}`",
            f"- Next safe action: {gate['next_safe_action']}",
            "",
            "## Official Sources",
            "",
        ]
    )
    for source in payload["official_sources"]:
        lines.extend(
            [
                f"### {source['label']}",
                "",
                f"- URL: {source['url']}",
                f"- Verified fact: {source['verified_fact']}",
                "",
            ]
        )

    lines.extend(["## Claim Boundary", "", payload["claim_boundary"], ""])
    rendered = "\n".join(lines)
    validate_public_redaction(
        {"rendered_markdown": rendered, "control_sha256": payload["control_sha256"]},
        {
            "application_number": None,
            "payment_received_date": None,
            "evidence": [],
        },
    )
    return rendered


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build private and public-safe patent deadline evidence controls."
    )
    parser.add_argument("--payment-acknowledgement", action="append", type=Path, default=[])
    parser.add_argument("--payment-receipt-screenshot", action="append", type=Path, default=[])
    parser.add_argument("--filing-receipt", action="append", type=Path, default=[])
    parser.add_argument("--official-correspondence", action="append", type=Path, default=[])
    parser.add_argument("--official-status-record", action="append", type=Path, default=[])
    parser.add_argument("--claims-record", action="append", type=Path, default=[])
    parser.add_argument("--application-number")
    parser.add_argument("--application-type")
    parser.add_argument("--payment-received-date")
    parser.add_argument("--basic-filing-fee-only-observed", action="store_true")
    parser.add_argument("--private-output", type=Path, default=PRIVATE_OUT)
    parser.add_argument("--public-json", type=Path, default=OUT_JSON)
    parser.add_argument("--public-markdown", type=Path, default=OUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    role_paths = {
        "payment_acknowledgement": args.payment_acknowledgement,
        "payment_receipt_screenshot": args.payment_receipt_screenshot,
        "filing_receipt": args.filing_receipt,
        "official_correspondence": args.official_correspondence,
        "official_status_record": args.official_status_record,
        "claims_record": args.claims_record,
    }
    private_payload = build_private_payload(
        records=collect_evidence(role_paths),
        application_number=args.application_number,
        application_type=args.application_type,
        payment_received_date=args.payment_received_date,
        basic_filing_fee_only_observed=args.basic_filing_fee_only_observed,
    )
    public_payload = build_public_payload(private_payload)
    rendered = render_markdown(public_payload)
    validate_public_redaction(public_payload, private_payload)
    validate_public_redaction(
        {"rendered_markdown": rendered, "control_sha256": public_payload["control_sha256"]},
        private_payload,
    )
    write_json(args.private_output, private_payload)
    write_json(args.public_json, public_payload)
    write_text(args.public_markdown, rendered)
    print(
        json.dumps(
            {
                "status": public_payload["status"],
                "source_count": private_payload["summary"]["source_count"],
                "unique_source_count": private_payload["summary"]["unique_source_count"],
                "private_output": str(args.private_output),
                "public_json": str(args.public_json),
                "public_markdown": str(args.public_markdown),
                "private_values_printed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
