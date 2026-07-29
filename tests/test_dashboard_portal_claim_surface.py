from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "BUILD_DASHBOARD_PORTAL.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_dashboard_portal", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_portal_leads_with_current_negative_evidence_contract(tmp_path):
    module = load_module()
    module.DASH = tmp_path
    module.HTML_OUT = tmp_path / "dashboard_portal.html"
    module.INDEX_OUT = tmp_path / "index.html"

    module.main()

    html = module.HTML_OUT.read_text(encoding="utf-8")
    assert "No Current Performance Champion" in html
    assert "482/1525" in html
    assert "-0.508191" in html
    assert "Global Promotions" in html
    assert ">0</div>" in html
    assert "0/6" in html
    assert "No Current Dollar Projection" in html
    assert 'href="data/source_native_family_baseline_ledger.json"' in html
    assert "Claimable Annual Estimate</div><div class=\"value\">$0.00" in html
    assert "hashes prove byte identity and deployment custody only, not model skill" in html
    assert "Reviewer-Safe Winner State" not in html
    assert "Current strongest family" not in html


def test_portal_embeds_no_champion_and_no_marketing_state(tmp_path):
    module = load_module()
    module.DASH = tmp_path
    module.HTML_OUT = tmp_path / "dashboard_portal.html"
    module.INDEX_OUT = tmp_path / "index.html"

    module.main()

    html = module.HTML_OUT.read_text(encoding="utf-8")
    assert '"internal_performance_champion_present": false' in html
    assert '"model_performance_marketing_allowed": false' in html
    assert '"direct_all_baseline_global_holm_positive_count": 0' in html


def test_dashboard_index_redirects_to_the_generated_existing_portal(tmp_path):
    module = load_module()
    module.DASH = tmp_path
    module.HTML_OUT = tmp_path / "dashboard_portal.html"
    module.INDEX_OUT = tmp_path / "index.html"

    module.main()

    index = module.INDEX_OUT.read_text(encoding="utf-8")
    assert 'url=dashboard_portal.html' in index
    assert 'href="dashboard_portal.html"' in index
    assert module.HTML_OUT.is_file()
    assert "operator_home.html" not in index


def test_portal_validator_rejects_retired_winner_language():
    module = load_module()

    with pytest.raises(ValueError, match="blocked claim phrases"):
        module.validate_portal_claim_surface(
            "Reviewer-Safe Winner State: Current strongest family"
        )
