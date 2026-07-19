from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DEADLINE_EVIDENCE_BRIDGE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("deadline_evidence_bridge", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bridge_promotes_measured_rows_and_keeps_claim_gates_false():
    module = load_module()
    payload = module.build_bridge(check_docker=False)

    assert payload["schema"] == "deadline_evidence_bridge_v1"
    assert payload["summary"]["live_measured_sources"] >= 17
    assert payload["summary"]["live_total_measured_rows"] >= 418
    assert payload["summary"]["geometry_families_ranked"] >= 75
    assert payload["summary"]["field_validation_claim_ready"] is False
    assert payload["summary"]["real_dollar_claim_ready"] is False
    assert "realized savings" in payload["summary"]["claim_boundary"]
    assert any(
        f"{payload['summary']['live_measured_sources']} measured sources" in item
        for item in payload["use_today"]
    )


def test_whitehole_is_custody_evidence_not_performance_evidence():
    module = load_module()
    payload = module.build_bridge(check_docker=False)
    whitehole = payload["whitehole"]

    assert whitehole["freeze_zip_count"] >= 1
    assert whitehole["latest_freeze"]["usable_as"] == "custody_and_reproducibility_evidence"
    assert whitehole["latest_freeze_selection"] == "newest_complete_freeze_with_sha256_sidecar"
    assert whitehole["latest_observed_freeze"]
    assert "not field validation" in whitehole["grant_limit"]
    assert "SHA256" in module.read_text_safe(Path(whitehole["latest_freeze"]["manifest"]), 1000)


def test_tooling_classifies_node_red_as_measurement_plumbing_only():
    module = load_module()
    payload = module.build_bridge(check_docker=False)
    tooling = payload["local_tooling"]

    assert tooling["node_red"]["grant_use"].startswith("Fast local demo")
    assert "do not build a new dependency today" in tooling["node_red"]["deadline_priority"]
    assert "distributed data-processing" in tooling["spark"]["what_it_is"]
    assert "not needed" in tooling["spark"]["deadline_priority"]


def test_linkedin_resume_drafts_are_evidence_bounded():
    module = load_module()
    payload = module.build_bridge(check_docker=False)
    drafts = payload["linkedin_resume_drafts"]

    assert "LumenCore" in drafts["linkedin_headline"]
    assert "hashable" in drafts["linkedin_about"]
    assert "field-validation readiness" in drafts["linkedin_about"]
    assert "Do not claim field validation" in drafts["safe_language_rule"]
    assert all("guaranteed" not in bullet.lower() for bullet in drafts["resume_bullets"])


def test_markdown_is_deadline_focused_and_safe():
    module = load_module()
    payload = module.build_bridge(check_docker=False)
    rendered = module.render_markdown(payload)

    assert "Deadline Evidence Bridge" in rendered
    assert "Use Today" in rendered
    assert "Do Not Overclaim" in rendered
    assert "Node-RED available" in rendered
    assert "award certainty" not in rendered.lower()
    assert "guaranteed profit" not in rendered.lower()
