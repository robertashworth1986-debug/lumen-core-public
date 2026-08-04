from __future__ import annotations

import importlib.util
import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_ERDC_SDC_PRIVATE_FINAL_CANDIDATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "erdc_sdc_private_final_candidate",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def synthetic_identity_payload() -> dict:
    timestamp = current_timestamp()
    return {
        "schema": "lumencore.erdc_sdc_private_final.v1",
        "opportunity_number": "W912HZ26SC005",
        "template_only": False,
        "legal_entity_name": "Synthetic Test Entity LLC",
        "solution_address": {
            "lines": ["100 Fixture Lane"],
            "locality": "Testville",
            "region": "TS",
            "postal_code": "00000",
            "country": "United States",
        },
        "proposal_contact": {
            "name": "Synthetic Contact",
            "email": "synthetic.contact@invalid.test",
            "verified_current": True,
        },
        "sam_verification": {
            "all_awards_registration_active": True,
            "exact_legal_name_match": True,
            "exact_solution_address_match": True,
            "verified_utc": timestamp,
        },
        "delivery": {
            "classified_work_proposed": False,
            "evaluator_status": "REQUESTED_NOT_COMMITTED",
            "government_or_prime_integration_owner": True,
            "production_cloud_capacity_committed": False,
            "production_hpc_allocation_committed": False,
            "support_boundary": "BOUNDED_PHASE_II_PROTOTYPE_SUPPORT_ONLY",
            "technical_lead_role": "Founder / Principal Investigator",
            "technical_lead_status": "PROPOSED",
            "transition_owner": "GOVERNMENT_OR_SELECTED_PRIME",
        },
        "certifications": {
            "delivery_boundaries_supported": True,
            "facts_current": True,
            "founder_approved_private_pdf_candidate": True,
            "no_invented_commitments": True,
            "private_identity_authorized_for_proposal": True,
        },
        "approval_utc": timestamp,
    }


def synthetic_rom_payload() -> dict:
    return {
        "schema": "lumencore.erdc_sdc_phase2_rom_private.v1",
        "opportunity_number": "W912HZ26SC005",
        "scope": "PHASE_II_PROTOTYPE_DEVELOPMENT_ONLY",
        "period_weeks": 16,
        "template_only": False,
        "direct_labor": [
            {
                "role": "Synthetic test engineer",
                "hours": "100",
                "rate_usd": "100.00",
                "rate_basis": "Synthetic fixture only",
            }
        ],
        "fringe": {"rate_pct": "20", "base": "DIRECT_LABOR"},
        "indirect": {
            "rate_pct": "25",
            "base": "DIRECT_LABOR_PLUS_FRINGE",
        },
        "other_direct_costs": [
            {
                "name": "Synthetic cloud fixture",
                "amount_usd": "1000.00",
                "basis": "Synthetic fixture only",
            }
        ],
        "ffp_risk_reserve_pct": "10",
        "profit_pct": "5",
        "rounding_increment_usd": "1000.00",
        "candidate_price_usd": "18000.00",
        "certifications": {
            "direct_labor_rate_supported": True,
            "indirect_treatment_supported": True,
            "other_direct_costs_itemized": True,
            "phase_iii_and_iv_costs_excluded": True,
            "no_uncommitted_subcontractor_costs": True,
            "founder_approved_candidate_price": True,
        },
        "approval_utc": current_timestamp(),
    }


def test_template_is_non_submittable_and_contains_no_private_values():
    module = load_module()
    template = json.loads(module.TEMPLATE.read_text(encoding="utf-8"))

    assert template["template_only"] is True
    assert template["legal_entity_name"] is None
    assert template["solution_address"]["lines"] == []
    assert template["proposal_contact"]["email"] is None
    assert template["sam_verification"]["all_awards_registration_active"] is False
    assert all(value is False for value in template["certifications"].values())
    assert template["delivery"] == module.EXPECTED_DELIVERY


def test_valid_private_identity_passes_without_returning_source_payload():
    module = load_module()
    result = module.validate_private_identity(synthetic_identity_payload())

    assert set(result) == {
        "legal_entity_name",
        "solution_address",
        "proposal_contact_name",
        "proposal_contact_email",
    }
    assert result["proposal_contact_email"].endswith("@invalid.test")
    assert "100 Fixture Lane" in result["solution_address"]


@pytest.mark.parametrize(
    ("mutator", "error_code"),
    [
        (
            lambda payload: payload["sam_verification"].update(
                verified_utc=(
                    datetime.now(timezone.utc) - timedelta(days=4)
                ).isoformat()
            ),
            "SAM_VERIFIED_UTC_STALE",
        ),
        (
            lambda payload: payload["delivery"].update(
                production_hpc_allocation_committed=True
            ),
            "DELIVERY_BOUNDARY_MISMATCH",
        ),
        (
            lambda payload: payload["certifications"].update(
                no_invented_commitments=False
            ),
            "CERTIFICATION_NO_INVENTED_COMMITMENTS_REQUIRED",
        ),
        (
            lambda payload: payload["proposal_contact"].update(
                email="not-an-email"
            ),
            "PROPOSAL_CONTACT_EMAIL_INVALID",
        ),
        (
            lambda payload: payload.update(template_only=True),
            "TEMPLATE_CANNOT_BE_USED_AS_PRIVATE_INPUT",
        ),
    ],
)
def test_private_identity_failures_are_fixed_codes(mutator, error_code):
    module = load_module()
    payload = deepcopy(synthetic_identity_payload())
    mutator(payload)

    with pytest.raises(module.PrivateFinalError) as exc:
        module.validate_private_identity(payload)

    assert exc.value.code == error_code


def test_public_gate_never_exposes_private_values_paths_or_amounts():
    module = load_module()
    result = module.baseline_result()
    payload = module.build_public_payload(
        result,
        status="PRIVATE_FINAL_INPUTS_NOT_CAPTURED",
    )
    serialized = json.dumps(payload, sort_keys=True)
    markdown = module.render_markdown(payload)

    module.ensure_public_safe(
        payload,
        forbidden_private_values=[
            "Synthetic Test Entity LLC",
            "100 Fixture Lane",
            "synthetic.contact@invalid.test",
        ],
    )
    assert payload["submission_ready"] is False
    assert payload["private_inputs"]["private_values_exposed"] is False
    assert payload["private_inputs"]["private_paths_exposed"] is False
    assert payload["private_inputs"]["private_fingerprints_exposed"] is False
    assert payload["controls"]["external_send_allowed"] is False
    assert payload["controls"]["final_portal_submit_allowed"] is False
    assert re.search(r"\$\s*\d", serialized) is None
    assert re.search(r"\$\s*\d", markdown) is None
    assert ".private.json" not in serialized
    assert "PRIVATE_FINAL_CANDIDATE_BUILD" in payload["unresolved_gates"]
    assert "HUMAN_UPLOAD_AND_FINAL_CONFIRMATION" in payload["unresolved_gates"]


def test_public_preflight_resolves_only_safe_public_dependencies():
    module = load_module()
    result = module.public_preflight_result()
    payload = module.build_public_payload(
        result,
        status="PRIVATE_FINAL_INPUTS_NOT_CAPTURED",
    )

    assert result["public_preflight_checked"] is True
    assert result["public_preflight_error_code"] is None
    assert result["source_gate_pass"] is True
    assert result["evidence_gate_pass"] is True
    assert payload["validation"]["official_source_integrity"] is True
    assert payload["validation"]["bounded_evidence_receipt"] is True
    assert "CURRENT_OFFICIAL_SOURCE_INTEGRITY" not in payload["unresolved_gates"]
    assert "BOUNDED_EVIDENCE_RECEIPT" not in payload["unresolved_gates"]
    assert "PRIVATE_IDENTITY_CAPTURE_AND_AUTHORIZATION" in payload[
        "unresolved_gates"
    ]
    assert "APPROVED_PHASE_II_ONLY_ROM" in payload["unresolved_gates"]
    assert payload["submission_ready"] is False


def test_public_safety_rejects_amounts_and_private_values():
    module = load_module()

    with pytest.raises(module.PrivateFinalError) as amount_error:
        module.ensure_public_safe({"leak": "$18,000.00"})
    assert amount_error.value.code == "PRIVATE_DOLLAR_AMOUNT_EXPOSED"

    with pytest.raises(module.PrivateFinalError) as identity_error:
        module.ensure_public_safe(
            {"leak": "Synthetic Test Entity LLC"},
            forbidden_private_values=["Synthetic Test Entity LLC"],
        )
    assert identity_error.value.code == "PRIVATE_VALUE_EXPOSED"


def test_full_synthetic_private_candidate_passes_and_is_removed():
    module = load_module()
    token = uuid4().hex
    identity_path = module.PRIVATE_DIR / f"pytest_identity_{token}.private.json"
    rom_path = module.PRIVATE_DIR / f"pytest_rom_{token}.private.json"
    output_path = module.PRIVATE_DIR / f"pytest_candidate_{token}.pdf"
    module.PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        identity_path.write_text(
            json.dumps(synthetic_identity_payload(), indent=2) + "\n",
            encoding="utf-8",
        )
        rom_path.write_text(
            json.dumps(synthetic_rom_payload(), indent=2) + "\n",
            encoding="utf-8",
        )

        result = module.build_private_candidate(
            private_input=identity_path,
            rom_input=rom_path,
            output_pdf=output_path,
        )

        assert output_path.is_file()
        assert result["candidate_built"] is True
        assert result["rom_gate_pass"] is True
        assert result["sam_gate_pass"] is True
        assert result["pdf_checks"]["all_checks_pass"] is True
        assert result["pdf_checks"]["exactly_one_phase_ii_total"] is True
        assert result["pdf_checks"]["forbidden_final_markers_absent"] is True
        assert result["pdf_checks"]["draft_watermark_absent"] is True
        assert result["pdf_checks"]["active_content_absent"] is True
    finally:
        for path in (identity_path, rom_path, output_path):
            if path.exists():
                path.unlink()


def test_written_public_gate_is_blocked_and_redacted():
    module = load_module()
    payload = json.loads(module.OUT_JSON.read_text(encoding="utf-8"))
    markdown = module.OUT_MD.read_text(encoding="utf-8")
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "PRIVATE_FINAL_INPUTS_NOT_CAPTURED"
    assert payload["submission_ready"] is False
    assert payload["private_final_candidate_built"] is False
    assert payload["private_inputs"]["private_values_exposed"] is False
    assert payload["private_inputs"]["private_paths_exposed"] is False
    assert payload["private_inputs"]["private_fingerprints_exposed"] is False
    assert payload["validation"]["public_preflight_checked"] is True
    assert payload["validation"]["public_preflight_error_code"] is None
    assert payload["validation"]["official_source_integrity"] is True
    assert payload["validation"]["bounded_evidence_receipt"] is True
    assert "CURRENT_OFFICIAL_SOURCE_INTEGRITY" not in payload["unresolved_gates"]
    assert "BOUNDED_EVIDENCE_RECEIPT" not in payload["unresolved_gates"]
    assert re.search(r"\$\s*\d", serialized) is None
    assert re.search(r"\$\s*\d", markdown) is None
    assert len(payload["gate_sha256"]) == 64
