from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FROZEN_DELTA_BUYER_OUTREACH.py"


@pytest.fixture
def sources(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("buyer_outreach", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    harvest = tmp_path / "harvest.json"
    intake = tmp_path / "intake.json"
    harvest.write_text(json.dumps({
        "generated_utc": "2026-09-22T11:00:00Z",
        "summary": {
            "measured_sources": 9, "total_measured_rows": 1234,
            "total_live_context_rows_evaluated": 98,
            "candidate_beats_named_baseline_count": 1,
            "registered_baseline_comparison_count": 22,
            "registered_baseline_mean_win_count": 10,
            "registered_baseline_global_holm_positive_count": 0,
            "rolling_champion_count": 0, "triple_source_candidate_count": 0,
            "ready_for_real_dollar_claim": True,
        },
    }), encoding="utf-8")
    intake.write_text(json.dumps({
        "generated_utc": "2026-09-22T10:00:00Z",
        "summary": {"files_seen": 401, "candidate_count": 32, "live_frozen_triple_threat_candidate_count": 4, "content_hash_count": 21},
        "top_candidates": [{"path": "E:/private-client-name/secret.pdf", "evidence_class": "PRIVATE_LABEL", "matched_groups": ["PRIVATE_BODY"]}],
    }), encoding="utf-8")
    monkeypatch.setattr(module, "HARVEST_JSON", harvest)
    monkeypatch.setattr(module, "EXTERNAL_INTAKE_JSON", intake)
    monkeypatch.setattr(module, "now_utc", lambda: "2026-09-22T12:00:00+00:00")
    return module, harvest, intake


def test_claims_and_templates_use_actual_dated_counts_and_preserve_nonwins(sources):
    module, harvest, intake = sources
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    assert payload["schema"] == "frozen_delta_buyer_outreach.v1"
    assert payload["decision_state"] == "HOLD_EXTERNAL_VALIDATION"
    assert payload["unknown_or_invalid_count_fields"] == []
    for key in ("technical_buyer_short", "government_teaming_partner"):
        body = payload["email_templates"][key]["body"]
        assert "9 sources marked measured" in body
        assert "1,234 source rows" in body
        assert "98 live-context replay rows" in body
        assert "2026-09-22T11:00:00+00:00" in body
        assert "10 mean wins among 22 registered comparisons" in body
        assert "0 globally Holm-positive comparisons" in body
        assert "0 rolling champions" in body
        assert "417 measured rows" not in body
        assert "3 candidate wins" not in body
    assert "field validation: `false`" in rendered.lower()
    assert "ready for real-dollar claim: `false`" in rendered.lower()
    assert "Do not mass email" in rendered
    assert "paid pilot" in rendered.lower()
    for key, path in [("harvest", harvest), ("external_intake", intake)]:
        receipt = payload["source_receipts"][key]
        raw = path.read_bytes()
        assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
        assert receipt["bytes"] == len(raw)
        assert receipt["read_utc"] == "2026-09-22T12:00:00+00:00"
        assert receipt["source_freshness"] == "CURRENT"
        assert receipt["underlying_artifacts_verified"] is False


def test_upstream_ready_flag_cannot_authorize_claims_or_sends(sources):
    module, _, _ = sources
    payload = module.build_payload()
    truth = payload["current_truth"]
    assert truth["reported_ready_for_real_dollar_claim"] is True
    assert truth["ready_for_real_dollar_claim"] is False
    assert truth["verified_annual_savings_usd"] is None
    assert truth["financial_effect_verified"] is False
    assert truth["field_validation"] is False
    assert truth["kraken_live_execution_allowed"] is False
    assert payload["send_gate"]["mass_email_allowed"] is False
    assert payload["send_gate"]["send_without_user_review"] is False


def test_private_intake_candidates_never_enter_public_payload_or_markdown(sources):
    module, _, _ = sources
    payload = module.build_payload()
    public = json.dumps(payload) + module.render_markdown(payload)
    assert payload["top_external_candidates"] == []
    for private_text in ["private-client-name", "secret.pdf", "PRIVATE_LABEL", "PRIVATE_BODY"]:
        assert private_text not in public


def test_missing_sources_remain_unknown_not_zero_or_current(sources):
    module, harvest, intake = sources
    harvest.unlink()
    intake.unlink()
    payload = module.build_payload()
    assert payload["decision_state"] == "HOLD_SOURCE_REVIEW"
    assert payload["current_truth"]["measured_sources"] is None
    assert payload["current_truth"]["rolling_champion_count"] is None
    assert "UNKNOWN sources marked measured" in payload["email_templates"]["technical_buyer_short"]["body"]
    for receipt in payload["source_receipts"].values():
        assert receipt["status"] == "MISSING"
        assert receipt["sha256"] is None
        assert receipt["source_freshness"] == "UNKNOWN"


@pytest.mark.parametrize("count", [None, True, -1, 2.5, "22"])
def test_invalid_count_types_remain_unknown(sources, count):
    module, harvest, _ = sources
    value = json.loads(harvest.read_text())
    value["summary"]["measured_sources"] = count
    harvest.write_text(json.dumps(value))
    payload = module.build_payload()
    assert payload["current_truth"]["measured_sources"] is None
    assert "measured_sources" in payload["unknown_or_invalid_count_fields"]
    assert payload["decision_state"] == "HOLD_SOURCE_REVIEW"


@pytest.mark.parametrize("raw", [b'{"summary": {}, "summary": {}}', b'{"summary": {"measured_sources": NaN}}', b'{"summary": {"measured_sources": 1e999}}', b'[]', b'{broken'])
def test_invalid_source_json_keeps_identity_but_no_numeric_claim(sources, raw):
    module, harvest, _ = sources
    harvest.write_bytes(raw)
    payload = module.build_payload()
    receipt = payload["source_receipts"]["harvest"]
    assert receipt["status"] == "INVALID_JSON"
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert payload["current_truth"]["measured_sources"] is None
    assert payload["decision_state"] == "HOLD_SOURCE_REVIEW"
    json.dumps(payload, allow_nan=False)


@pytest.mark.parametrize("stamp,status", [("2026-07-29T00:00:00Z", "STALE"), ("2026-09-23T00:00:00Z", "FUTURE_TIMESTAMP"), ("2026-09-22T11:00:00", "INVALID_TIMESTAMP"), ("not a timestamp", "INVALID_TIMESTAMP")])
def test_source_time_is_not_replaced_by_builder_time(sources, stamp, status):
    module, harvest, _ = sources
    value = json.loads(harvest.read_text())
    value["generated_utc"] = stamp
    harvest.write_text(json.dumps(value))
    payload = module.build_payload()
    assert payload["source_receipts"]["harvest"]["source_freshness"] == status
    assert payload["decision_state"] == "HOLD_SOURCE_REVIEW"
    assert payload["current_truth"]["ready_for_real_dollar_claim"] is False


def test_contradictory_comparison_counts_preserved_and_flagged(sources):
    module, harvest, _ = sources
    value = json.loads(harvest.read_text())
    value["summary"]["registered_baseline_mean_win_count"] = 23
    harvest.write_text(json.dumps(value))
    payload = module.build_payload()
    assert payload["current_truth"]["registered_baseline_mean_win_count"] == 23
    assert payload["count_consistency_issues"] == ["registered_baseline_mean_win_count_exceeds_registered_comparisons"]
    assert payload["decision_state"] == "HOLD_SOURCE_REVIEW"
