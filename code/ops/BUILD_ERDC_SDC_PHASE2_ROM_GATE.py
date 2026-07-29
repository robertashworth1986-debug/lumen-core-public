from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
SOURCE_DIR = SPRINT_DIR / "source_attachments" / "W912HZ26SC005"
SOURCE_MANIFEST = SOURCE_DIR / "SOURCE_MANIFEST_2026-07-29.json"
PRIVATE_DIR = SPRINT_DIR / "private" / "W912HZ26SC005"
DEFAULT_PRIVATE_INPUT = PRIVATE_DIR / "ERDC_SDC_PHASE2_ROM.private.json"
TEMPLATE = ROOT / "config" / "erdc_sdc_phase2_rom_private_template_v1.json"
OUT_JSON = SPRINT_DIR / "ERDC_SDC_PHASE2_ROM_GATE_2026-07-29.json"
OUT_MD = SPRINT_DIR / "ERDC_SDC_PHASE2_ROM_GATE_2026-07-29.md"

PRIVATE_SCHEMA = "lumencore.erdc_sdc_phase2_rom_private.v1"
PUBLIC_SCHEMA = "lumencore.erdc_sdc_phase2_rom_gate.v2"
OPPORTUNITY_NUMBER = "W912HZ26SC005"
PHASE_II_SCOPE = "PHASE_II_PROTOTYPE_DEVELOPMENT_ONLY"
PLANNING_PERIOD_WEEKS = 16
REQUIRED_CERTIFICATIONS = (
    "direct_labor_rate_supported",
    "indirect_treatment_supported",
    "other_direct_costs_itemized",
    "phase_iii_and_iv_costs_excluded",
    "no_uncommitted_subcontractor_costs",
    "founder_approved_candidate_price",
)
PRIVATE_AMOUNT_FIELDS = {
    "amount_usd",
    "candidate_price_usd",
    "hours",
    "profit_pct",
    "rate_pct",
    "rate_usd",
    "rounding_increment_usd",
}
PUBLIC_CLAIM_BOUNDARY = (
    "This public gate proves only that the private Phase II pricing workflow is structurally "
    "available and, when explicitly invoked, can verify arithmetic and approval flags without "
    "publishing private rates or dollar amounts. It is not a quote, certified accounting record, "
    "proposal submission, contract, award, Government price determination, SAM verification, or "
    "authorization to accept terms. Phase III and Phase IV costs are excluded."
)


class RomGateError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def parse_decimal(value: Any, field: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise RomGateError(f"INVALID_{field.upper()}")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise RomGateError(f"INVALID_{field.upper()}") from None
    if not amount.is_finite() or amount < 0 or (positive and amount <= 0):
        raise RomGateError(f"INVALID_{field.upper()}")
    return amount


def parse_percentage(value: Any, field: str, maximum: Decimal) -> Decimal:
    rate = parse_decimal(value, field)
    if rate > maximum:
        raise RomGateError(f"INVALID_{field.upper()}")
    return rate


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def git_ignored(path: Path) -> bool:
    if not path_is_within(path, ROOT):
        return False
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def validate_private_target(path: Path) -> Path:
    if path.is_symlink():
        raise RomGateError("PRIVATE_INPUT_SYMLINK_REJECTED")
    resolved = path.resolve()
    if not path_is_within(resolved, PRIVATE_DIR):
        raise RomGateError("PRIVATE_INPUT_OUTSIDE_BOUNDED_DIRECTORY")
    if resolved.exists() and not resolved.is_file():
        raise RomGateError("PRIVATE_INPUT_NOT_REGULAR_FILE")
    if not git_ignored(resolved):
        raise RomGateError("PRIVATE_INPUT_NOT_GIT_IGNORED")
    return resolved


def rounded_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    if increment <= 0:
        raise RomGateError("INVALID_ROUNDING_INCREMENT_USD")
    units = (value / increment).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (units * increment).quantize(Decimal("0.01"))


def validate_approval_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def calculate_private_rom(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != PRIVATE_SCHEMA:
        raise RomGateError("PRIVATE_SCHEMA_MISMATCH")
    if payload.get("opportunity_number") != OPPORTUNITY_NUMBER:
        raise RomGateError("OPPORTUNITY_NUMBER_MISMATCH")
    if payload.get("scope") != PHASE_II_SCOPE:
        raise RomGateError("PHASE_SCOPE_MISMATCH")
    if payload.get("period_weeks") != PLANNING_PERIOD_WEEKS:
        raise RomGateError("PERIOD_WEEKS_MISMATCH")
    if payload.get("template_only") is True:
        raise RomGateError("TEMPLATE_CANNOT_BE_USED_AS_PRIVATE_INPUT")

    labor_rows = payload.get("direct_labor")
    if not isinstance(labor_rows, list) or not labor_rows:
        raise RomGateError("DIRECT_LABOR_REQUIRED")
    direct_labor = Decimal("0")
    for row in labor_rows:
        if not isinstance(row, dict) or not str(row.get("role", "")).strip():
            raise RomGateError("DIRECT_LABOR_ROLE_REQUIRED")
        if not str(row.get("rate_basis", "")).strip():
            raise RomGateError("DIRECT_LABOR_RATE_BASIS_REQUIRED")
        hours = parse_decimal(row.get("hours"), "labor_hours", positive=True)
        rate = parse_decimal(row.get("rate_usd"), "labor_rate_usd", positive=True)
        direct_labor += hours * rate

    fringe = payload.get("fringe")
    if not isinstance(fringe, dict) or fringe.get("base") != "DIRECT_LABOR":
        raise RomGateError("FRINGE_BASE_MISMATCH")
    fringe_rate = parse_percentage(fringe.get("rate_pct"), "fringe_rate_pct", Decimal("100"))
    fringe_cost = direct_labor * fringe_rate / Decimal("100")

    indirect = payload.get("indirect")
    if not isinstance(indirect, dict) or indirect.get("base") != "DIRECT_LABOR_PLUS_FRINGE":
        raise RomGateError("INDIRECT_BASE_MISMATCH")
    indirect_rate = parse_percentage(
        indirect.get("rate_pct"), "indirect_rate_pct", Decimal("200")
    )
    indirect_cost = (direct_labor + fringe_cost) * indirect_rate / Decimal("100")

    direct_cost_rows = payload.get("other_direct_costs")
    if not isinstance(direct_cost_rows, list) or not direct_cost_rows:
        raise RomGateError("OTHER_DIRECT_COSTS_REQUIRED")
    direct_cost_names: set[str] = set()
    other_direct_costs = Decimal("0")
    for row in direct_cost_rows:
        if not isinstance(row, dict):
            raise RomGateError("INVALID_OTHER_DIRECT_COST")
        name = str(row.get("name", "")).strip()
        basis = str(row.get("basis", "")).strip()
        if not name or not basis or name.casefold() in direct_cost_names:
            raise RomGateError("INVALID_OTHER_DIRECT_COST")
        direct_cost_names.add(name.casefold())
        other_direct_costs += parse_decimal(row.get("amount_usd"), "other_direct_cost_usd")

    risk_rate = parse_percentage(
        payload.get("ffp_risk_reserve_pct"), "ffp_risk_reserve_pct", Decimal("100")
    )
    profit_rate = parse_percentage(payload.get("profit_pct"), "profit_pct", Decimal("100"))
    increment = parse_decimal(
        payload.get("rounding_increment_usd"), "rounding_increment_usd", positive=True
    )
    candidate_price = parse_decimal(
        payload.get("candidate_price_usd"), "candidate_price_usd", positive=True
    )

    cost_subtotal = direct_labor + fringe_cost + indirect_cost + other_direct_costs
    risk_reserve = cost_subtotal * risk_rate / Decimal("100")
    pre_profit = cost_subtotal + risk_reserve
    profit = pre_profit * profit_rate / Decimal("100")
    unrounded_price = pre_profit + profit
    formula_price = rounded_to_increment(unrounded_price, increment)
    if candidate_price.quantize(Decimal("0.01")) != formula_price:
        raise RomGateError("CANDIDATE_PRICE_DOES_NOT_MATCH_FORMULA")

    certifications = payload.get("certifications")
    if not isinstance(certifications, dict):
        raise RomGateError("CERTIFICATIONS_REQUIRED")
    certification_state = {
        key: certifications.get(key) is True for key in REQUIRED_CERTIFICATIONS
    }
    approval_timestamp_present = validate_approval_timestamp(payload.get("approval_utc"))
    founder_approved = certification_state["founder_approved_candidate_price"]
    all_cost_basis_gates_pass = all(
        certification_state[key]
        for key in REQUIRED_CERTIFICATIONS
        if key != "founder_approved_candidate_price"
    )
    ready = founder_approved and approval_timestamp_present and all_cost_basis_gates_pass

    return {
        "candidate_sha256": stable_hash(payload),
        "labor_role_count": len(labor_rows),
        "other_direct_cost_count": len(direct_cost_rows),
        "arithmetic_checked": True,
        "candidate_matches_formula": True,
        "phase_ii_only": True,
        "phase_iii_and_iv_costs_excluded": certification_state[
            "phase_iii_and_iv_costs_excluded"
        ],
        "certification_state": certification_state,
        "approval_timestamp_present": approval_timestamp_present,
        "founder_approved": founder_approved,
        "all_cost_basis_gates_pass": all_cost_basis_gates_pass,
        "rom_ready_for_private_pdf_insertion": ready,
        "private_amounts": {
            "direct_labor": direct_labor,
            "fringe": fringe_cost,
            "indirect": indirect_cost,
            "other_direct_costs": other_direct_costs,
            "risk_reserve": risk_reserve,
            "profit": profit,
            "formula_price": formula_price,
        },
    }


def source_integrity() -> dict[str, Any]:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for item in manifest["files"]:
        path = ROOT / item["path"]
        actual_hash = sha256_file(path)
        actual_bytes = path.stat().st_size
        rows.append(
            {
                "path": item["path"],
                "sha256_match": actual_hash == item["sha256"],
                "bytes_match": actual_bytes == item["bytes"],
            }
        )
    return {
        "manifest_schema": manifest.get("schema"),
        "manifest_as_of_date": manifest.get("as_of_date"),
        "current_attachment_set_complete": manifest.get(
            "current_attachment_set_complete"
        ),
        "manifest_path": rel(SOURCE_MANIFEST),
        "manifest_sha256": sha256_file(SOURCE_MANIFEST),
        "files": rows,
        "all_checks_pass": (
            all(row["sha256_match"] and row["bytes_match"] for row in rows)
            and manifest.get("schema") == "lumencore.erdc_sdc_source_manifest.v2"
            and manifest.get("as_of_date") == "2026-07-29"
            and manifest.get("current_attachment_set_complete") is True
        ),
    }


def unresolved_gates(calculation: dict[str, Any] | None) -> list[str]:
    if calculation is None:
        return [
            "PRIVATE_INPUT_CAPTURE",
            "DIRECT_RATE_SUPPORT",
            "INDIRECT_TREATMENT",
            "OTHER_DIRECT_COST_ITEMIZATION",
            "NO_UNCOMMITTED_SUBCONTRACTOR_COSTS",
            "FOUNDER_CANDIDATE_PRICE_APPROVAL",
            "PRIVATE_PDF_INSERTION",
            "SAM_ALL_AWARDS_IDENTITY_ADDRESS_AND_CONTRACT_STATUS_MATCH",
            "CURRENT_PROPOSAL_CONTACT_EMAIL",
            "SUBMITTABLE_ACCOUNT_AND_COMPLETE_FORM_ACCESS",
            "PORTAL_PREVIEW_TERMS_AND_FINAL_CONFIRMATION",
        ]
    flags = calculation["certification_state"]
    gates = []
    mapping = {
        "direct_labor_rate_supported": "DIRECT_RATE_SUPPORT",
        "indirect_treatment_supported": "INDIRECT_TREATMENT",
        "other_direct_costs_itemized": "OTHER_DIRECT_COST_ITEMIZATION",
        "phase_iii_and_iv_costs_excluded": "PHASE_III_AND_IV_EXCLUSION",
        "no_uncommitted_subcontractor_costs": "NO_UNCOMMITTED_SUBCONTRACTOR_COSTS",
        "founder_approved_candidate_price": "FOUNDER_CANDIDATE_PRICE_APPROVAL",
    }
    for key, gate in mapping.items():
        if not flags[key]:
            gates.append(gate)
    if not calculation["approval_timestamp_present"]:
        gates.append("FOUNDER_APPROVAL_TIMESTAMP")
    gates.extend(
        [
            "PRIVATE_PDF_INSERTION",
            "SAM_ALL_AWARDS_IDENTITY_ADDRESS_AND_CONTRACT_STATUS_MATCH",
            "CURRENT_PROPOSAL_CONTACT_EMAIL",
            "SUBMITTABLE_ACCOUNT_AND_COMPLETE_FORM_ACCESS",
            "PORTAL_PREVIEW_TERMS_AND_FINAL_CONFIRMATION",
        ]
    )
    return gates


def build_payload(
    private_payload: dict[str, Any] | None = None,
    *,
    private_input_sha256: str | None = None,
) -> dict[str, Any]:
    sources = source_integrity()
    calculation = calculate_private_rom(private_payload) if private_payload is not None else None
    gates = unresolved_gates(calculation)
    rom_ready = bool(calculation and calculation["rom_ready_for_private_pdf_insertion"])
    if not sources["all_checks_pass"]:
        status = "OFFICIAL_SOURCE_INTEGRITY_FAILED"
    elif private_payload is None:
        status = "PRIVATE_ROM_INPUT_NOT_CAPTURED"
    elif rom_ready:
        status = "ROM_APPROVED_PRIVATE_PDF_SAM_AND_PORTAL_FINALIZATION_REQUIRED"
    else:
        status = "PRIVATE_ROM_VALIDATED_APPROVAL_OR_COST_BASIS_GATES_OPEN"

    payload: dict[str, Any] = {
        "schema": PUBLIC_SCHEMA,
        "generated_utc": now_utc(),
        "opportunity_number": OPPORTUNITY_NUMBER,
        "deadline": {
            "controlling_cso_pdf_text": "1700 EST, 07 AUG 2026",
            "current_live_page_text": "4:00 PM CT on August 7, 2026",
            "safest_operational_cutoff": "4:00 PM CT on August 7, 2026",
            "reconciliation_rule": (
                "Preserve both source texts and complete before the current live "
                "page's earlier practical cutoff."
            ),
        },
        "status": status,
        "submission_ready": False,
        "phase_scope": PHASE_II_SCOPE,
        "period_weeks": PLANNING_PERIOD_WEEKS,
        "period_semantics": "INTERNAL_PLANNING_ASSUMPTION_NOT_ERDC_MANDATED",
        "funding_currently_available": False,
        "private_input": {
            "expected_path": rel(DEFAULT_PRIVATE_INPUT),
            "git_ignored_target": git_ignored(DEFAULT_PRIVATE_INPUT),
            "present": private_payload is not None,
            "fingerprint_exposed": False,
            "private_values_exposed": False,
        },
        "arithmetic": {
            "checked": bool(calculation),
            "candidate_matches_formula": bool(
                calculation and calculation["candidate_matches_formula"]
            ),
            "candidate_price_present": bool(calculation),
            "candidate_price_value_exposed": False,
            "private_row_counts_exposed": False,
        },
        "approval": {
            "founder_approved": bool(calculation and calculation["founder_approved"]),
            "approval_timestamp_present": bool(
                calculation and calculation["approval_timestamp_present"]
            ),
            "rom_ready_for_private_pdf_insertion": rom_ready,
        },
        "unresolved_gates": gates,
        "source_integrity": sources,
        "controls": {
            "external_send_allowed": False,
            "final_portal_submit_allowed": False,
            "sam_private_values_allowed_in_public_output": False,
            "browser_navigation_performed": False,
            "phase_iii_or_iv_costs_allowed": False,
        },
        "formula": (
            "candidate price = round_to_increment(((direct labor + fringe + indirect + "
            "other direct costs) * (1 + FFP risk reserve rate)) * (1 + profit rate))"
        ),
        "private_template": rel(TEMPLATE),
        "claim_boundary": PUBLIC_CLAIM_BOUNDARY,
        "outputs": {"json": rel(OUT_JSON), "markdown": rel(OUT_MD)},
    }
    payload["gate_sha256"] = stable_hash(payload)
    ensure_public_safe(payload)
    return payload


def ensure_public_safe(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    lowered = serialized.casefold()
    forbidden_key_hits = [
        key for key in PRIVATE_AMOUNT_FIELDS if f'"{key}"' in lowered
    ]
    if forbidden_key_hits:
        raise RomGateError("PRIVATE_AMOUNT_FIELD_EXPOSED")
    if re.search(r"\$\s*\d", serialized):
        raise RomGateError("PRIVATE_DOLLAR_AMOUNT_EXPOSED")


def render_markdown(payload: dict[str, Any]) -> str:
    private = payload["private_input"]
    arithmetic = payload["arithmetic"]
    approval = payload["approval"]
    lines = [
        "# ERDC SDC Phase II ROM Gate - 2026-07-29",
        "",
        "This public-safe gate converts the remaining estimated-price blocker into a private, auditable workflow without publishing any rate or dollar amount.",
        "",
        "## Decision",
        "",
        f"- Status: `{payload['status']}`",
        f"- Submission ready: `{str(payload['submission_ready']).lower()}`",
        f"- Safest operational deadline: `{payload['deadline']['safest_operational_cutoff']}`",
        f"- Original CSO PDF deadline text: `{payload['deadline']['controlling_cso_pdf_text']}`",
        f"- Current live page deadline text: `{payload['deadline']['current_live_page_text']}`",
        f"- Scope: `{payload['phase_scope']}`",
        f"- Proposed period: `{payload['period_weeks']}` weeks",
        f"- Funding currently available: `{str(payload['funding_currently_available']).lower()}`",
        f"- Private input present: `{str(private['present']).lower()}`",
        f"- Private target git-ignored: `{str(private['git_ignored_target']).lower()}`",
        f"- Private values exposed: `{str(private['private_values_exposed']).lower()}`",
        f"- Arithmetic checked: `{str(arithmetic['checked']).lower()}`",
        f"- Candidate matches formula: `{str(arithmetic['candidate_matches_formula']).lower()}`",
        f"- Candidate price value exposed: `{str(arithmetic['candidate_price_value_exposed']).lower()}`",
        f"- Founder approved: `{str(approval['founder_approved']).lower()}`",
        f"- ROM ready for private PDF insertion: `{str(approval['rom_ready_for_private_pdf_insertion']).lower()}`",
        f"- Session-browser navigation performed: `{str(payload['controls']['browser_navigation_performed']).lower()}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
        "## Formula",
        "",
        payload["formula"],
        "",
        "## Unresolved Gates",
        "",
    ]
    lines.extend(f"- `{gate}`" for gate in payload["unresolved_gates"])
    lines.extend(
        [
            "",
            "## Private Workflow",
            "",
            f"1. Copy `{payload['private_template']}` to the ignored private input path.",
            "2. Replace every placeholder with a supported cost basis and one candidate price.",
            "3. Invoke this builder explicitly with `--private-input`; its public output contains only gates, counts, and hashes.",
            "4. Insert the approved amount only into the private ERDC PDF after the cost basis and founder-approval gates pass.",
            "5. Separately verify the SAM legal identity, matching address, contract registration, portal fields, terms, and final confirmation.",
            "",
            "## Official Source Integrity",
            "",
        ]
    )
    for row in payload["source_integrity"]["files"]:
        lines.append(
            f"- `{row['path']}`: hash=`{str(row['sha256_match']).lower()}` bytes=`{str(row['bytes_match']).lower()}`"
        )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def load_private_input(path: Path) -> tuple[dict[str, Any], str]:
    target = validate_private_target(path)
    if not target.is_file():
        raise RomGateError("PRIVATE_INPUT_NOT_FOUND")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise RomGateError("PRIVATE_INPUT_NOT_VALID_JSON") from None
    if not isinstance(payload, dict):
        raise RomGateError("PRIVATE_INPUT_NOT_OBJECT")
    return payload, sha256_file(target)


def write_public_outputs(payload: dict[str, Any]) -> None:
    markdown = render_markdown(payload)
    if re.search(r"\$\s*\d", markdown):
        raise RomGateError("PRIVATE_DOLLAR_AMOUNT_EXPOSED")
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    OUT_MD.write_text(markdown, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a public-safe ERDC Phase II ROM gate without exposing private amounts."
    )
    parser.add_argument(
        "--private-input",
        type=Path,
        help="Explicit ignored private input path under the bounded ERDC directory.",
    )
    parser.add_argument(
        "--check-target",
        action="store_true",
        help="Verify the default private target is bounded and ignored without reading it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.check_target:
            target = validate_private_target(DEFAULT_PRIVATE_INPUT)
            result = {
                "status": "PRIVATE_TARGET_READY",
                "path": rel(target),
                "exists": target.exists(),
                "git_ignored": True,
                "private_values_read_or_printed": False,
                "browser_navigation_performed": False,
            }
        elif args.private_input:
            private_payload, private_hash = load_private_input(args.private_input)
            payload = build_payload(
                private_payload, private_input_sha256=private_hash
            )
            write_public_outputs(payload)
            result = {
                "status": payload["status"],
                "private_input_present": True,
                "private_values_printed": False,
                "rom_ready_for_private_pdf_insertion": payload["approval"][
                    "rom_ready_for_private_pdf_insertion"
                ],
                "browser_navigation_performed": False,
                "json": rel(OUT_JSON),
            }
        else:
            payload = build_payload()
            write_public_outputs(payload)
            result = {
                "status": payload["status"],
                "private_input_present": False,
                "private_values_printed": False,
                "browser_navigation_performed": False,
                "json": rel(OUT_JSON),
            }
        print(json.dumps(result, indent=2, sort_keys=True))
    except RomGateError as exc:
        print(
            json.dumps(
                {
                    "status": "ROM_GATE_NOT_COMPLETED",
                    "error_code": exc.code,
                    "private_values_printed": False,
                    "browser_navigation_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
