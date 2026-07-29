import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_TAKEOFF_ONBOARDING_REVIEW_PACKET_2026-07-29.md"
)
PPTX = (
    ROOT
    / "output"
    / "pptx"
    / "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pptx"
)
PDF = (
    ROOT
    / "output"
    / "pdf"
    / "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pdf"
)
LEDGER = ROOT / "out" / "ops" / "source_native_family_baseline_ledger_latest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_onboarding_packet_binds_current_deck_and_evidence_counts() -> None:
    text = PACKET.read_text(encoding="utf-8")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    summary = ledger["summary"]

    assert f"`{PPTX.stat().st_size}` bytes" in text
    assert f"SHA-256 `{sha256(PPTX)}`" in text
    assert f"`{PDF.stat().st_size}` bytes" in text
    assert f"SHA-256 `{sha256(PDF)}`" in text

    assert f"`{summary['registered_family_count']}` registered families" in text
    assert f"`{summary['implementation_present_count']}` implementations present" in text
    assert (
        f"`{summary['executed_direct_source_baseline_comparison_count']}` "
        "executed direct comparisons"
    ) in text
    assert (
        f"`{summary['exploratory_direct_comparison_count']}` exploratory"
    ) in text
    assert (
        f"`{summary['confirmatory_protocol_comparison_count']}` "
        "confirmatory-protocol comparisons"
    ) in text
    assert (
        f"`{summary['individual_comparison_global_holm_positive_count']}` "
        "global Holm-positive comparisons"
    ) in text
    assert (
        f"`{summary['internal_source_native_promotion_gate_pass_count']}` "
        "promoted champions"
    ) in text


def test_onboarding_packet_remains_founder_gated_and_claim_bounded() -> None:
    text = PACKET.read_text(encoding="utf-8")

    assert "Do not check agreement boxes, sign, upload, pay, or submit" in text
    assert "Final submit" in text
    assert "Deposit and any payment terms" in text
    assert "does not prove revenue, customers, market validation" in text
