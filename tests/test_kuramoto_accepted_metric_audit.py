from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_KURAMOTO_ACCEPTED_METRIC_AUDIT.py"
REQUIRED_EVIDENCE = [
    ROOT / "out" / "ops" / "kuramoto_holdout_expansion_latest.json",
    ROOT / "dashboard" / "data" / "champion_phase_proxy_diagnostics.json",
    ROOT / "dashboard" / "data" / "baseline_gauntlet_coverage.json",
]


def load_module():
    spec = importlib.util.spec_from_file_location("kuramoto_accepted_metric_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def require_local_evidence_feeds():
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_EVIDENCE if not path.exists()]
    if missing:
        pytest.skip(f"local ignored evidence feeds are unavailable: {', '.join(missing)}")


def test_kuramoto_accepted_metric_audit_maps_supported_proxy_metrics():
    require_local_evidence_feeds()
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    by_id = {row["metric_id"]: row for row in payload["accepted_metric_rows"]}

    assert payload["schema"] == "kuramoto_accepted_metric_audit_v1"
    assert summary["champion_family"] == "kuramoto_phase_coupling"
    assert summary["wins_vs_named_baseline"] >= 20
    assert summary["accepted_metric_proxy_language_allowed"] is True
    assert by_id["kuramoto_order_parameter_proxy"]["status"] == "REPLAY_PROXY_READY"
    assert by_id["kuramoto_phase_bound_stress_proxy"]["status"] == "REPLAY_PROXY_READY"


def test_kuramoto_accepted_metric_audit_keeps_external_claims_blocked():
    require_local_evidence_feeds()
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    by_id = {row["metric_id"]: row for row in payload["accepted_metric_rows"]}

    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert by_id["kuramoto_critical_coupling_threshold"]["status"] == "EXTERNAL_TOPOLOGY_REQUIRED"
    assert by_id["ieee_grid_case_replay"]["status"] == "IMPLEMENTATION_OR_DATASET_NEEDED"

    dumped = json.dumps(payload).lower()
    assert "does not establish field validation" in dumped
    assert "critical coupling" in dumped
    assert "ieee 39/118/300" in dumped


def test_kuramoto_accepted_metric_audit_markdown_is_reviewer_safe():
    require_local_evidence_feeds()
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Kuramoto Accepted Metric Audit" in rendered
    assert "Accepted Metric Map" in rendered
    assert "Field validation claim allowed: `false`" in rendered
    assert "not a field-validation certificate" in rendered
