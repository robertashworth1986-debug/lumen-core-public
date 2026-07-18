from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SUBMISSION_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
PRIVATE_DIR = SUBMISSION_DIR / "private"
MANIFEST_SCHEMA = "lumencore.nashville_ec_fall_2026_application.v1"
FOUNDER_MAP_SCHEMA = "lumencore.nashville_ec_private_portal_fill_map.v1"
CONTACT_MAP_SCHEMA = "lumencore.nashville_ec_private_contact_map.v1"
OUTPUT_SCHEMA = "lumencore.nashville_ec_private_complete_portal_preview.v1"
PUBLIC_READY_STATUSES = {
    "READY",
    "READY_NO_FEE_COMMITMENT",
    "CONDITIONAL_NOT_APPLICABLE",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def output_path_allowed(path: Path) -> bool:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return True
    try:
        resolved.relative_to(PRIVATE_DIR.resolve())
    except ValueError:
        return False
    return True


def require_object(payload: Any, name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON object")
    return payload


def answer_map(
    payload: dict[str, Any],
    *,
    schema: str,
    name: str,
) -> dict[int, dict[str, Any]]:
    if payload.get("schema") != schema:
        raise ValueError(f"{name} schema must be {schema}")
    rows = payload.get("question_answers")
    if not isinstance(rows, list):
        raise ValueError(f"{name}.question_answers must be a list")
    mapped: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("question_id"), int):
            raise ValueError(f"Every {name} answer must have an integer question_id")
        question_id = row["question_id"]
        if question_id in mapped:
            raise ValueError(f"Duplicate {name} question_id: {question_id}")
        mapped[question_id] = row
    return mapped


def validate_manifest(manifest: dict[str, Any]) -> dict[int, dict[str, Any]]:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(f"manifest schema must be {MANIFEST_SCHEMA}")
    fields = manifest.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("manifest.fields must be a nonempty list")
    mapped: dict[int, dict[str, Any]] = {}
    for row in fields:
        if not isinstance(row, dict) or not isinstance(row.get("question_id"), int):
            raise ValueError("Every manifest field must have an integer question_id")
        question_id = row["question_id"]
        if question_id in mapped:
            raise ValueError(f"Duplicate manifest question_id: {question_id}")
        if not isinstance(row.get("required"), bool):
            raise ValueError(f"Q{question_id} required must be true or false")
        mapped[question_id] = row
    return mapped


def build_preview(
    manifest: dict[str, Any],
    founder_map: dict[str, Any],
    contact_map: dict[str, Any],
    *,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    manifest = require_object(manifest, "manifest")
    founder_map = require_object(founder_map, "founder_map")
    contact_map = require_object(contact_map, "contact_map")
    fields_by_id = validate_manifest(manifest)
    founder_answers = answer_map(
        founder_map, schema=FOUNDER_MAP_SCHEMA, name="founder_map"
    )
    contact_answers = answer_map(
        contact_map, schema=CONTACT_MAP_SCHEMA, name="contact_map"
    )

    founder_ids_expected = {
        question_id
        for question_id, row in fields_by_id.items()
        if row.get("status") == "HUMAN_CONFIRM_REQUIRED"
    }
    contact_ids_allowed = {
        question_id
        for question_id, row in fields_by_id.items()
        if row.get("status") == "PRIVATE_PORTAL_ENTRY"
    }
    if set(founder_answers) != founder_ids_expected:
        missing = sorted(founder_ids_expected - set(founder_answers))
        extra = sorted(set(founder_answers) - founder_ids_expected)
        raise ValueError(
            f"Founder answer coverage mismatch; missing={missing}, extra={extra}"
        )
    if not set(contact_answers).issubset(contact_ids_allowed):
        extra = sorted(set(contact_answers) - contact_ids_allowed)
        raise ValueError(f"Unexpected private contact question_ids: {extra}")

    assembled_fields: list[dict[str, Any]] = []
    required_unresolved: list[int] = []
    status_counts: dict[str, int] = {}
    for source in manifest["fields"]:
        question_id = source["question_id"]
        status = source["status"]
        answer: Any = source["proposed_answer"]
        entry_status: str

        if question_id in founder_answers:
            answer = founder_answers[question_id].get("value")
            if answer is None or answer == "":
                raise ValueError(f"Founder answer Q{question_id} cannot be empty")
            entry_status = "READY_PRIVATE_FOUNDER_ATTESTATION"
        elif status == "PRIVATE_PORTAL_ENTRY":
            contact = contact_answers.get(question_id)
            if contact is None:
                entry_status = "REQUIRED_PRIVATE_CONTACT_MISSING"
            elif contact.get("value") not in (None, ""):
                answer = contact["value"]
                entry_status = "READY_PRIVATE_CONTACT"
            elif not source["required"] and contact.get("disposition") == "OMIT_OPTIONAL":
                answer = None
                entry_status = "OPTIONAL_OMITTED"
            else:
                entry_status = "REQUIRED_PRIVATE_CONTACT_MISSING"
        elif status in PUBLIC_READY_STATUSES:
            entry_status = "READY_PUBLIC_PACKET"
        elif status == "OPTIONAL_FOUNDER_CHOICE":
            answer = None
            entry_status = "OPTIONAL_OMITTED"
        else:
            entry_status = "UNRESOLVED"

        if source["required"] and entry_status in {
            "REQUIRED_PRIVATE_CONTACT_MISSING",
            "UNRESOLVED",
        }:
            required_unresolved.append(question_id)
        status_counts[entry_status] = status_counts.get(entry_status, 0) + 1
        assembled_fields.append(
            {
                "question_id": question_id,
                "section": source["section"],
                "label": source["label"],
                "required": source["required"],
                "answer": answer,
                "entry_status": entry_status,
                "evidence_basis": source["evidence"],
            }
        )

    required_total = sum(1 for row in manifest["fields"] if row["required"])
    payload: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "generated_utc": generated_utc or now_utc(),
        "status": (
            "PORTAL_FILL_ASSEMBLED_FINAL_HUMAN_ACTION_GATED"
            if not required_unresolved
            else "REQUIRED_PRIVATE_FIELDS_MISSING"
        ),
        "private_portal_only": True,
        "public_repo_publish_allowed": False,
        "opportunity": manifest["opportunity"],
        "program_economics": manifest["program_economics"],
        "summary": {
            "field_count": len(assembled_fields),
            "required_field_count": required_total,
            "required_ready_count": required_total - len(required_unresolved),
            "required_unresolved_count": len(required_unresolved),
            "required_unresolved_question_ids": required_unresolved,
            "founder_attestation_answer_count": len(founder_answers),
            "private_contact_answer_count": sum(
                1
                for row in contact_answers.values()
                if row.get("value") not in (None, "")
            ),
            "status_counts": status_counts,
        },
        "fields": assembled_fields,
        "financial_classification_guardrail": {
            "question_62_founder_cash": (
                "Founder-funded estimate for business compute, equipment, internet, and AI; "
                "not outside funding or money raised."
            ),
            "question_63_grants": "Grant award funds received only.",
            "question_64_investor_capital": "Outside investor capital received only.",
            "revenue": "Customer business revenue only; founder spending is not revenue.",
        },
        "final_action_gate": {
            "all_required_answers_assembled": not required_unresolved,
            "live_portal_preview_reviewed": False,
            "fee_and_terms_reviewed": False,
            "final_submission_authorized_at_action_time": False,
            "submission_performed": False,
        },
        "claim_boundary": (
            "This private artifact assembles portal answers from a public-safe application "
            "packet, founder attestations, and authenticated contact data. It does not "
            "independently verify the attestations, accept fees or terms, submit the form, "
            "or establish program acceptance, revenue, funding, or validation."
        ),
    }
    payload["portal_preview_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Nashville EC Private Portal Preview",
        "",
        f"Status: `{payload['status']}`",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"SHA-256: `{payload['portal_preview_sha256']}`",
        "",
        "## Readiness",
        "",
        f"- Required answers ready: `{summary['required_ready_count']}/{summary['required_field_count']}`",
        f"- Founder attestations incorporated: `{summary['founder_attestation_answer_count']}`",
        "- Final portal review, fee/terms review, and submission remain human-gated.",
        "",
        "## Portal Answers",
        "",
    ]
    for row in payload["fields"]:
        answer = "[leave blank]" if row["answer"] is None else str(row["answer"])
        lines.extend(
            [
                f"### Q{row['question_id']} - {row['label']}",
                "",
                f"- Required: `{str(row['required']).lower()}`",
                f"- Entry status: `{row['entry_status']}`",
                f"- Answer: {answer}",
                "",
            ]
        )
    lines.extend(
        [
            "## Financial Classification",
            "",
            "- Founder cash is self-funded business spend, not outside funding or revenue.",
            "- Grants and investor capital remain zero unless funds were actually received.",
            "",
            "## Final Action Gate",
            "",
            "- Review the live portal preview.",
            "- Review any fee, financial-aid, consent, and program-term language.",
            "- Submit only after the live answers match this private preview.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble a private Nashville EC portal preview from validated inputs."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--founder-map", required=True, type=Path)
    parser.add_argument("--contact-map", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=PRIVATE_DIR / "nashville_ec_complete_portal_preview.private.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    markdown = output.with_suffix(".md")
    if not output_path_allowed(output) or not output_path_allowed(markdown):
        raise SystemExit(
            "Refusing to write a private portal preview into a tracked repository path. "
            f"Use {PRIVATE_DIR} or a path outside the repository."
        )
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    founder_map = json.loads(args.founder_map.read_text(encoding="utf-8-sig"))
    contact_map = json.loads(args.contact_map.read_text(encoding="utf-8-sig"))
    payload = build_preview(manifest, founder_map, contact_map)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "required_ready": payload["summary"]["required_ready_count"],
                "required_total": payload["summary"]["required_field_count"],
                "output": str(output),
                "markdown": str(markdown),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
