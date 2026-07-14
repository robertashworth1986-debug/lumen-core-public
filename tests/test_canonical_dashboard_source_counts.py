from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MISSION_CONTROL = ROOT / "dashboard" / "mission_control.html"
QUANT_LAB = ROOT / "dashboard" / "quant_lab.html"


def test_mission_control_prefers_current_hash_backed_source_register() -> None:
    html = MISSION_CONTROL.read_text(encoding="utf-8")

    assert "data/measured_source_evidence_register.json" in html
    assert "current_probe_hash_backed_measured_sources" in html
    assert "current_probe_enabled_sources" in html
    assert "current_probe_coverage_pct" in html
    assert "current hash-backed coverage" in html
    assert "source register required" in html
    assert "no current source count is inferred" in html


def test_quant_lab_prefers_current_hash_backed_source_register() -> None:
    html = QUANT_LAB.read_text(encoding="utf-8")

    assert "data/measured_source_evidence_register.json" in html
    assert "sourceRegister?.summary?.current_probe_hash_backed_measured_sources" in html
    assert "sourceRegister?.summary?.current_probe_enabled_sources" in html
    assert "sourceRegister?.summary?.current_probe_hash_backed_measured_sources\n    ?? breadth" not in html
    assert "sourceRegister?.summary?.current_probe_enabled_sources\n    ?? breadth" not in html
    assert "grid-template-columns: minmax(0, 1fr);" in html
    assert ".ql-bar, .ql-pulse, .ql-side, .ql-main" in html
    assert ".ql-continuity-v { overflow-wrap: anywhere; white-space: normal; }" in html


def test_mission_control_whitelists_bounded_value_fields() -> None:
    html = MISSION_CONTROL.read_text(encoding="utf-8")

    assert "allowed_estimated_hourly_value_usd" in html
    assert "allowed_estimated_annual_value_usd" in html
    assert "context-only values withheld" in html
    assert "WITHHELD" in html
    assert "NOT SHOWN" in html
    for blocked_key in (
        "blocked_context_only_annual_value_usd",
        "sector_capture_math",
        "gross_value_usd",
        "recommended_avoided_cost_usd",
        "translated_annual_value_usd",
        "trader.hourly_value_usd",
        "row.total_estimated_hourly_value_usd",
    ):
        assert blocked_key not in html
