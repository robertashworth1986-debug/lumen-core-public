from __future__ import annotations

import importlib.util
import hashlib
import json
import re
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_ERDC_SDC_PHASE2_ROM_GATE.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "ERDC_SDC_PHASE2_ROM_GATE_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("erdc_sdc_phase2_rom_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def synthetic_private_payload() -> dict:
    return {
        "schema": "lumencore.erdc_sdc_phase2_rom_private.v1",
        "opportunity_number": "W912HZ26SC005",
        "scope": "PHASE_II_PROTOTYPE_DEVELOPMENT_ONLY",
        "period_weeks": 16,
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
        "approval_utc": "2026-07-17T10:00:00Z",
    }


def test_default_private_target_is_bounded_and_git_ignored():
    module = load_module()
    target = module.validate_private_target(module.DEFAULT_PRIVATE_INPUT)

    assert target == module.DEFAULT_PRIVATE_INPUT.resolve()
    assert module.git_ignored(target) is True


def test_private_template_is_non_submittable_and_contains_no_amounts():
    module = load_module()
    template = json.loads(module.TEMPLATE.read_text(encoding="utf-8"))

    assert template["template_only"] is True
    assert template["scope"] == module.PHASE_II_SCOPE
    assert template["candidate_price_usd"] is None
    assert template["direct_labor"][0]["hours"] is None
    assert template["direct_labor"][0]["rate_usd"] is None
    assert all(value is False for value in template["certifications"].values() if value is not True)


def test_synthetic_private_candidate_arithmetic_and_approval_pass():
    module = load_module()
    result = module.calculate_private_rom(synthetic_private_payload())

    assert result["arithmetic_checked"] is True
    assert result["candidate_matches_formula"] is True
    assert result["phase_ii_only"] is True
    assert result["private_amounts"]["formula_price"] == Decimal("18000.00")
    assert result["all_cost_basis_gates_pass"] is True
    assert result["founder_approved"] is True
    assert result["rom_ready_for_private_pdf_insertion"] is True


def test_public_gate_sanitizes_every_private_amount_and_rate():
    module = load_module()
    payload = module.build_payload(
        synthetic_private_payload(), private_input_sha256="a" * 64
    )
    serialized = json.dumps(payload, sort_keys=True)
    markdown = module.render_markdown(payload)

    assert payload["status"] == (
        "ROM_APPROVED_PRIVATE_PDF_SAM_AND_PORTAL_FINALIZATION_REQUIRED"
    )
    assert payload["submission_ready"] is False
    assert payload["private_input"]["private_values_exposed"] is False
    assert payload["arithmetic"]["candidate_price_value_exposed"] is False
    assert payload["approval"]["rom_ready_for_private_pdf_insertion"] is True
    assert "rate_usd" not in serialized
    assert "candidate_price_usd" not in serialized
    assert re.search(r"\$\s*\d", serialized) is None
    assert re.search(r"\$\s*\d", markdown) is None
    assert "PRIVATE_PDF_INSERTION" in payload["unresolved_gates"]
    assert "SAM_IDENTITY_ADDRESS_AND_CONTRACT_STATUS_MATCH" in payload["unresolved_gates"]
    assert "PORTAL_PREVIEW_TERMS_AND_FINAL_CONFIRMATION" in payload["unresolved_gates"]


def test_default_public_gate_stays_blocked_without_private_input():
    module = load_module()
    payload = module.build_payload()

    assert payload["status"] == "PRIVATE_ROM_INPUT_NOT_CAPTURED"
    assert payload["private_input"]["present"] is False
    assert payload["arithmetic"]["checked"] is False
    assert payload["approval"]["founder_approved"] is False
    assert payload["controls"]["external_send_allowed"] is False
    assert payload["controls"]["final_portal_submit_allowed"] is False
    assert payload["controls"]["browser_navigation_performed"] is False
    assert payload["source_integrity"]["all_checks_pass"] is True


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (
            lambda payload: payload.update(scope="PHASE_III_DEMONSTRATION"),
            "PHASE_SCOPE_MISMATCH",
        ),
        (
            lambda payload: payload.update(candidate_price_usd="17000.00"),
            "CANDIDATE_PRICE_DOES_NOT_MATCH_FORMULA",
        ),
        (
            lambda payload: payload["indirect"].update(base="DIRECT_LABOR"),
            "INDIRECT_BASE_MISMATCH",
        ),
        (
            lambda payload: payload["direct_labor"][0].update(rate_usd="-1"),
            "INVALID_LABOR_RATE_USD",
        ),
        (
            lambda payload: payload.update(template_only=True),
            "TEMPLATE_CANNOT_BE_USED_AS_PRIVATE_INPUT",
        ),
    ],
)
def test_invalid_private_candidates_fail_closed(mutator, code):
    module = load_module()
    payload = deepcopy(synthetic_private_payload())
    mutator(payload)

    with pytest.raises(module.RomGateError) as exc:
        module.calculate_private_rom(payload)

    assert exc.value.code == code


def test_written_public_outputs_are_sanitized_and_claim_bounded():
    module = load_module()
    payload = json.loads(module.OUT_JSON.read_text(encoding="utf-8"))
    markdown = module.OUT_MD.read_text(encoding="utf-8")
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "PRIVATE_ROM_INPUT_NOT_CAPTURED"
    assert payload["submission_ready"] is False
    assert payload["private_input"]["private_values_exposed"] is False
    assert payload["controls"]["browser_navigation_performed"] is False
    assert "rate_usd" not in serialized
    assert "candidate_price_usd" not in serialized
    assert re.search(r"\$\s*\d", serialized) is None
    assert re.search(r"\$\s*\d", markdown) is None
    assert "not a quote" in payload["claim_boundary"]
    assert len(payload["gate_sha256"]) == 64


def test_bounded_e_drive_mirror_matches_every_public_safe_artifact():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 7
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_input_mirrored"] is False
    assert receipt["private_amounts_present_in_public_artifacts"] is False
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        destination = Path(artifact["destination"])
        assert source.is_file(), artifact["source"]
        assert destination.is_file(), artifact["destination"]
        assert source.stat().st_size == destination.stat().st_size == artifact["bytes"]
        assert sha256_file(source) == sha256_file(destination) == artifact["sha256"]
