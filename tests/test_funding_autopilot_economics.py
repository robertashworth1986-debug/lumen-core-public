from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "funding_autopilot.py"


def load_module():
    spec = importlib.util.spec_from_file_location("funding_autopilot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def configure_inputs(monkeypatch, module, tmp_path: Path, *, sector=None, cross=None, evidence=None, summary=None):
    payloads = {
        "SECTOR_FILE": ("sector.json", sector or {}),
        "CROSS_FILE": ("cross.json", cross or {}),
        "EVIDENCE_FILE": ("evidence.json", evidence or {}),
        "INSTITUTIONAL_SUMMARY_FILE": ("summary.json", summary or {}),
    }
    for attribute, (filename, payload) in payloads.items():
        path = tmp_path / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(module, attribute, path)


def funding_item() -> dict:
    return {
        "ticket_id": "FUND-TEST-001",
        "title": "Bounded Funding Test",
        "channel": "grant",
        "agency": "Test Agency",
        "priority_score": 80,
        "deadline_utc": "2026-08-01T00:00:00+00:00",
        "estimated_value_usd": 5000,
    }


def test_missing_economic_inputs_never_receive_numeric_defaults(tmp_path, monkeypatch):
    module = load_module()
    configure_inputs(monkeypatch, module, tmp_path)

    anchor = module._build_evidence_anchor()

    assert anchor["prevented_pct"] is None
    assert anchor["pilot_sites"] is None
    assert anchor["savings_per_site_usd"] is None
    assert anchor["economic_evidence_status"] == "BLOCKED_MISSING_SOURCE_BOUND_ECONOMIC_SUPPORT"
    assert "missing_source_bound_metric:prevented_pct" in anchor["evidence_blockers"]
    assert "missing_source_bound_metric:pilot_sites" in anchor["evidence_blockers"]
    assert "missing_source_bound_metric:savings_per_site_usd" in anchor["evidence_blockers"]

    serialized = json.dumps(anchor, sort_keys=True)
    assert '"prevented_pct": 91.2' not in serialized
    assert '"pilot_sites": 20' not in serialized
    assert '"savings_per_site_usd": 183120' not in serialized


def test_explicit_zero_metrics_are_preserved_with_file_and_field_receipts(tmp_path, monkeypatch):
    module = load_module()
    configure_inputs(
        monkeypatch,
        module,
        tmp_path,
        cross={"recommended": {"prevented_pct": 0}},
        evidence={"pilot_sites": 0, "savings_per_site_usd": 0},
    )

    anchor = module._build_evidence_anchor()

    assert anchor["prevented_pct"] == 0
    assert anchor["pilot_sites"] == 0
    assert anchor["savings_per_site_usd"] == 0
    assert anchor["metric_receipts"]["prevented_pct"]["field"] == "recommended.prevented_pct"
    assert anchor["metric_receipts"]["pilot_sites"]["field"] == "pilot_sites"
    assert anchor["metric_receipts"]["savings_per_site_usd"]["field"] == "savings_per_site_usd"


def test_draft_marks_missing_metrics_and_omits_unsupported_positive_claims(tmp_path, monkeypatch):
    module = load_module()
    configure_inputs(monkeypatch, module, tmp_path)
    monkeypatch.setattr(module, "DRAFTS", tmp_path / "drafts")
    anchor = module._build_evidence_anchor()

    paths = module._write_draft(funding_item(), anchor)
    rendered = Path(paths["markdown"]).read_text(encoding="utf-8")

    assert "Failure prevention rate: NOT ESTABLISHED" in rendered
    assert "Pilot footprint: NOT ESTABLISHED" in rendered
    assert "Savings per site/year: NOT ESTABLISHED" in rendered
    assert "Funding accelerates sector deployment where benchmark outperformance" not in rendered
    assert "avoided-cost evidence already exist" not in rendered
    assert "No source-bound benchmark-outperformance claim is made" in rendered
    assert "No source-bound avoided-cost or realized-savings claim is made" in rendered
    assert "missing_source_bound_metric:pilot_sites" in rendered
    assert "91.2%" not in rendered
    assert "20 sites" not in rendered
    assert "$183.1K" not in rendered


def test_positive_claims_require_complete_source_bound_support(tmp_path, monkeypatch):
    module = load_module()
    benchmark_source = tmp_path / "benchmark_receipt.json"
    avoided_cost_source = tmp_path / "avoided_cost_receipt.json"
    benchmark_source.write_text('{"protocol_id":"locked-v1"}', encoding="utf-8")
    avoided_cost_source.write_text('{"calculation":"buyer-approved"}', encoding="utf-8")
    configure_inputs(
        monkeypatch,
        module,
        tmp_path,
        sector={
            "yearly_translated_value": 5000,
            "annual_upside_usd": 1000,
        },
        cross={"recommended": {"prevented_pct": 4.5}},
        evidence={
            "pilot_sites": 2,
            "savings_per_site_usd": 1250,
            "claim_support": {
                "benchmark_outperformance": {
                    "supported": True,
                    "source_refs": [str(benchmark_source)],
                    "named_baseline": "Named Incumbent v2",
                    "metric": "mean_absolute_error",
                    "protocol_id": "locked-v1",
                    "direction": "lower_is_better",
                    "candidate_value": 0.12,
                    "baseline_value": 0.2,
                },
                "avoided_cost": {
                    "supported": True,
                    "source_refs": [str(avoided_cost_source)],
                    "claim_level": "modeled_estimate",
                    "amount_usd": 2500,
                    "basis": "two cited pilot sites times the cited per-site estimate",
                },
            },
        },
    )
    monkeypatch.setattr(module, "DRAFTS", tmp_path / "drafts")

    anchor = module._build_evidence_anchor()
    assert anchor["economic_evidence_status"] == "SOURCE_BOUND_ECONOMIC_SUPPORT_COMPLETE"
    assert anchor["claim_support"]["benchmark_outperformance"]["supported"] is True
    assert anchor["claim_support"]["avoided_cost"]["supported"] is True

    paths = module._write_draft(funding_item(), anchor)
    rendered = Path(paths["markdown"]).read_text(encoding="utf-8")

    assert "Source-bound benchmark outperformance is limited to protocol locked-v1" in rendered
    assert "Named Incumbent v2" in rendered
    assert "source-bound modeled estimate avoided-cost amount of $2.5K" in rendered
    assert "This is not a realized-savings claim" in rendered
    assert str(benchmark_source.resolve()) in rendered
    assert str(avoided_cost_source.resolve()) in rendered


def test_claim_support_fails_closed_for_generic_baseline_or_missing_source(tmp_path, monkeypatch):
    module = load_module()
    configure_inputs(
        monkeypatch,
        module,
        tmp_path,
        cross={"recommended": {"prevented_pct": 1}},
        evidence={
            "pilot_sites": 1,
            "savings_per_site_usd": 100,
            "claim_support": {
                "benchmark_outperformance": {
                    "supported": True,
                    "source_refs": [str(tmp_path / "missing.json")],
                    "named_baseline": "baseline",
                    "metric": "score",
                    "protocol_id": "p1",
                    "direction": "higher_is_better",
                    "candidate_value": 2,
                    "baseline_value": 1,
                }
            },
        },
    )

    anchor = module._build_evidence_anchor()

    support = anchor["claim_support"]["benchmark_outperformance"]
    assert support["supported"] is False
    assert support["reason"] == "missing_or_invalid_local_source_refs"
    assert anchor["economic_evidence_status"] == "BLOCKED_MISSING_SOURCE_BOUND_ECONOMIC_SUPPORT"
