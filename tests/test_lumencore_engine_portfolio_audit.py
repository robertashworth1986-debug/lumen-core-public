from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_LUMENCORE_ENGINE_PORTFOLIO_AUDIT.py"
CONFIG_PATH = ROOT / "config" / "lumencore_engine_portfolio_v2.json"
PACKET_PATH = ROOT / "config" / "strategic_transaction_packet_v2.json"
GRAPH_PATH = ROOT / "config" / "evidence_graph_v1.json"
JSON_OUT = ROOT / "dashboard" / "data" / "lumencore_engine_portfolio_audit.json"
MD_OUT = ROOT / "docs" / "LUMENCORE_ENGINE_PORTFOLIO_AUDIT_2026-08-08.md"
EXPLAIN_PATH = ROOT / "dashboard" / "explain.html"


def load_module():
    spec = importlib.util.spec_from_file_location("engine_portfolio_audit", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def module():
    return load_module()


@pytest.fixture()
def inputs(module):
    return (
        module.read_json(CONFIG_PATH),
        module.read_json(PACKET_PATH),
        module.read_json(GRAPH_PATH),
    )


def build(module, inputs):
    registry, packet, graph = inputs
    return module.build_payload(registry, packet, graph, "2026-08-08T10:30:00Z")


def test_registry_has_exactly_fifteen_unique_lanes(inputs):
    registry, _, _ = inputs
    ids = [engine["id"] for engine in registry["engines"]]
    assert len(ids) == 15
    assert len(set(ids)) == 15
    assert sum(engine["lane"] == "priority_validation_lane" for engine in registry["engines"]) == 1


def test_one_platform_one_offer_one_priority_lane(module, inputs):
    payload = build(module, inputs)
    summary = payload["summary"]
    binding = payload["primary_offer_binding"]

    assert binding["platform"] == "LumenCore"
    assert binding["evidence_layer"] == "ProofLock"
    assert binding["primary_offer_id"] == "buyer-owned-baseline-validation-sprint"
    assert summary["primary_offer_count"] == 1
    assert summary["priority_lane_id"] == "lumen_infrastructure_sentinel"
    assert summary["priority_lane_scoping_candidate"] is True
    assert summary["direct_engine_sales_authorized"] is False


def test_current_commercial_truth_is_fail_closed(module, inputs):
    payload = build(module, inputs)
    summary = payload["summary"]

    assert summary["subscription_ready_count"] == 0
    assert summary["buyer_commitment_evidenced"] is False
    assert summary["signed_paid_scope_evidenced"] is False
    assert summary["executed_buyer_pilot_evidenced"] is False
    assert summary["revenue_evidenced"] is False
    assert summary["external_validation_evidenced"] is False


def test_audit_uses_tracked_repository_evidence(module, inputs):
    payload = build(module, inputs)
    by_id = {engine["id"]: engine for engine in payload["engines"]}

    assert by_id["lumengov_grant_factory"]["observed_maturity"] == "tested_implementation"
    assert by_id["lumen_infrastructure_sentinel"]["observed_maturity"] == "runnable_component"
    assert by_id["echoform_identity_engine"]["observed_maturity"] == "concept_only"
    assert by_id["smart_city_node_engine"]["observed_maturity"] == "concept_only"
    assert by_id["luma_xr_command_room"]["missing_paths"] == []
    assert payload["summary"]["missing_evidence_path_count"] == 0
    assert payload["summary"]["untracked_evidence_path_count"] == 0
    tracked_records = [
        record
        for engine in payload["engines"]
        for records in engine["evidence"].values()
        for record in records
        if record["tracked"]
    ]
    assert tracked_records
    assert all(len(record["git_blob_sha"]) == 40 for record in tracked_records)
    assert all(len(record["sha256"]) == 64 for record in tracked_records)


def test_public_payload_excludes_private_drive_and_branch_inventory(module, inputs):
    payload_text = json.dumps(build(module, inputs), sort_keys=True).lower()

    assert "supplemental_discovery" not in payload_text
    assert "private_local" not in payload_text
    assert "branch_candidate" not in payload_text
    assert "pr 36 head" not in payload_text
    assert "icloud" not in payload_text
    assert "c:\\" not in payload_text
    assert "e:\\" not in payload_text


def test_packet_text_drift_breaks_integrity_binding(module, inputs):
    registry, packet, graph = copy.deepcopy(inputs)
    packet["primary_offer"]["customer_problem"] += " drift"
    with pytest.raises(ValueError, match="strategic packet integrity mismatch"):
        module.build_payload(registry, packet, graph, "2026-08-08T10:30:00Z")


def test_graph_drift_breaks_offer_binding(module, inputs):
    registry, packet, graph = copy.deepcopy(inputs)
    graph["nodes"][0]["title"] += " drift"
    with pytest.raises(ValueError, match="evidence graph binding mismatch"):
        module.build_payload(registry, packet, graph, "2026-08-08T10:30:00Z")


def test_direct_engine_sales_cannot_be_enabled(module, inputs):
    registry, packet, graph = copy.deepcopy(inputs)
    registry["market_position"]["direct_engine_sales_authorized"] = True
    with pytest.raises(ValueError, match="direct engine sales"):
        module.build_payload(registry, packet, graph, "2026-08-08T10:30:00Z")


def test_payload_integrity_seals_all_public_content(module, inputs):
    payload = build(module, inputs)
    assert payload["integrity"]["payload_sha256"] == module.payload_sha256(payload)

    payload["engines"][0]["safe_description"] += " drift"
    assert payload["integrity"]["payload_sha256"] != module.payload_sha256(payload)


def test_markdown_keeps_one_offer_and_no_stale_sales_sequence(module, inputs):
    markdown = module.render_markdown(build(module, inputs))
    lowered = markdown.lower()

    assert "one platform with one primary commercial offer" in lowered
    assert "buyer-owned baseline validation sprint" in markdown
    assert "first revenue sequence" not in lowered
    assert "design_partner_ready" not in lowered
    assert "subscription-ready products: `0`" in lowered
    assert "buyer commitment evidenced: `false`" in lowered


def test_generated_outputs_match_current_inputs():
    subprocess.run(
        [sys.executable, str(MODULE_PATH), "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_check_reuses_existing_output_timestamp(tmp_path):
    json_out = tmp_path / "audit.json"
    md_out = tmp_path / "audit.md"
    command = [
        sys.executable,
        str(MODULE_PATH),
        "--json-out",
        str(json_out),
        "--md-out",
        str(md_out),
    ]
    subprocess.run(
        [*command, "--as-of-utc", "2026-08-08T10:30:00Z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [*command, "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_duplicate_json_key_rejected(module, tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"2.0","schema_version":"2.0"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        module.read_json(path)


def test_published_artifacts_exist():
    assert JSON_OUT.is_file()
    assert MD_OUT.is_file()


def test_explain_page_has_no_dead_local_html_links():
    text = EXPLAIN_PATH.read_text(encoding="utf-8")
    links = set(
        re.findall(r'(?:href\s*=\s*["\']|href:\s*["\'])([^"\']+\.html)', text)
    )
    assert links
    assert "./alpha_burst_lab_holo_3d.html" not in links
    assert "./scenario_mission.html" not in links
    for link in links:
        if link.startswith("https://lumen-core.ai/"):
            link = link.removeprefix("https://lumen-core.ai")
        target = (
            ROOT / "dashboard" / link.lstrip("/")
            if link.startswith("/")
            else EXPLAIN_PATH.parent / link
        )
        assert target.is_file(), link
