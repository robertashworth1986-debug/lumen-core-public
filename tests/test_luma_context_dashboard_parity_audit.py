from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LUMA_CONTEXT_DASHBOARD_PARITY_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("luma_context_dashboard_parity_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def audit_fixture(tmp_path, monkeypatch):
    module = load_module()
    root = tmp_path / "repo"
    docs = root / "docs"
    grants = root / "grant_submissions"
    out_ops = root / "out" / "ops"
    dashboard = root / "dashboard"
    dashboard_data = dashboard / "data"

    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "DOCS", docs)
    monkeypatch.setattr(module, "GRANTS", grants)
    monkeypatch.setattr(module, "OUT_OPS", out_ops)
    monkeypatch.setattr(module, "DASHBOARD", dashboard)
    monkeypatch.setattr(module, "DASHBOARD_DATA", dashboard_data)
    monkeypatch.setattr(module, "OUT_JSON", out_ops / "luma_context_dashboard_parity_audit_latest.json")
    monkeypatch.setattr(module, "OUT_MD", docs / "LUMA_CONTEXT_DASHBOARD_PARITY_AUDIT_2026-06-22.md")
    monkeypatch.setattr(module, "DASHBOARD_JSON", dashboard_data / "luma_context_dashboard_parity_audit.json")
    monkeypatch.setattr(
        module,
        "git_dirty_summary",
        lambda: {
            "available": True,
            "total_dirty_entries": 3,
            "counts_by_code": {" M": 2, "??": 1},
            "untracked_count": 1,
            "modified_count": 2,
            "added_count": 0,
            "sample": [" M dashboard/grants.html", "?? tests/new_test.py"],
            "policy": "Treat the dirty repo as active worktrail. Do not reset, checkout, delete, or clean generated artifacts.",
        },
    )

    context_checkpoints = [
        ("agent_continuity_rules", root / "AGENTS.md"),
        ("operating_memory", docs / "LUMAJARVIS_OPERATING_MEMORY_2026-06-20.md"),
        ("legendary_goal_prompt", docs / "LUMAJARVIS_LEGENDARY_GOAL_PROMPT_2026-06-21.md"),
        ("dashboard_architecture", docs / "DASHBOARD_ARCHITECTURE.md"),
        ("grant_deadline_triage", grants / "GRANT_DEADLINE_TRIAGE_2026-06-22.md"),
        ("top5_live_proof_board", grants / "TOP5_LIVE_PROOF_SUBMISSION_BOARD_2026-06-22.md"),
        ("geometry_frontier", docs / "GEOMETRY_PROOF_FRONTIER_BOARD_2026-06-22.md"),
        ("geometry_live_breadth_queue", docs / "GEOMETRY_LIVE_BREADTH_PROOF_QUEUE_2026-06-22.md"),
        ("public_visibility", docs / "PUBLIC_VISIBILITY_AND_SOURCE_AUTHORITY_2026-06-20.md"),
        ("local_icloud_intake", grants / "LOCAL_ICLOUD_EVIDENCE_INTAKE_2026-06-21.md"),
        ("patent_legal_rescue", grants / "PATENT_LEGAL_RESCUE_PACKET_2026-06-20.md"),
    ]
    monkeypatch.setattr(module, "CONTEXT_CHECKPOINTS", context_checkpoints)
    for key, path in context_checkpoints:
        write_text(path, f"# {key}\n")

    canonical_dashboards = [
        {
            "key": "mission_control",
            "route": "/mission_control.html",
            "path": dashboard / "mission_control.html",
            "role": "system health, evidence, approvals, operating posture",
            "must_show": ["live_proof_value_meter", "domain_parity", "claim_boundaries"],
        },
        {
            "key": "quant_lab",
            "route": "/quant_lab.html",
            "path": dashboard / "quant_lab.html",
            "role": "unified research cockpit and operator navigation host",
            "must_show": ["geometry_frontier", "kraken_truth", "live_proof_value_meter", "claim_boundaries"],
        },
        {
            "key": "grants",
            "route": "/grants.html",
            "path": dashboard / "grants.html",
            "role": "opportunity qualification, application readiness, submission workflow",
            "must_show": [
                "top5_live_proof",
                "live_proof_value_meter",
                "discarded_workspaces",
                "field_validation_targets",
            ],
        },
        {
            "key": "proof_to_pilot",
            "route": "/proof_to_pilot.html",
            "path": dashboard / "proof_to_pilot.html",
            "role": "field-validation gate, buyer-safe outreach, pilot conversion, claim controls",
            "must_show": [
                "proof_to_pilot_control_room",
                "field_validation_control_room",
                "field_validation_outreach_board",
                "buyer_authorized_replay",
                "claim_boundaries",
            ],
        },
    ]
    monkeypatch.setattr(module, "CANONICAL_DASHBOARDS", canonical_dashboards)

    write_text(
        dashboard / "mission_control.html",
        "<title>Mission</title> luma_command_fabric.js luma_context_dashboard_parity_audit "
        "grant_readiness_status live_proof_value_meter claim boundary",
    )
    write_text(
        dashboard / "quant_lab.html",
        "<title>Quant</title> luma_command_fabric.js luma_context_dashboard_parity_audit "
        "geometry_proof_frontier live_proof_value_meter kraken PAPER claim boundary",
    )
    write_text(
        dashboard / "grants.html",
        "<title>Grants</title> grant_readiness_status top5_live_proof live_proof_value_meter "
        "geometry_asset_wiring_board field-validation buyer-authorized replay discarded_workspaces",
    )
    write_text(
        dashboard / "proof_to_pilot.html",
        "<title>Proof To Pilot</title> proof_to_pilot_control_room field_validation_control_room "
        "field_validation_outreach_board buyer-authorized replay claim boundary",
    )

    local_feeds = [
        ("grant_readiness_status", dashboard_data / "grant_readiness_status.json"),
        ("top5_live_proof_submission_board", dashboard_data / "top5_live_proof_submission_board.json"),
        ("live_proof_value_meter", dashboard_data / "live_proof_value_meter.json"),
        ("geometry_asset_wiring_board", dashboard_data / "geometry_asset_wiring_board.json"),
        ("geometry_proof_frontier_board", dashboard_data / "geometry_proof_frontier_board.json"),
        ("geometry_live_breadth_proof_queue", dashboard_data / "geometry_live_breadth_proof_queue.json"),
        ("champion_metric_gauntlet", dashboard_data / "champion_metric_gauntlet.json"),
        ("field_validation_control_room", dashboard_data / "field_validation_control_room.json"),
        ("field_validation_outreach_board", dashboard_data / "field_validation_outreach_board.json"),
        ("proof_to_pilot_control_room", dashboard_data / "proof_to_pilot_control_room.json"),
    ]
    monkeypatch.setattr(module, "LOCAL_FEEDS", local_feeds)
    for key, path in local_feeds:
        write_json(path, {"schema": key, "generated_utc": "2026-06-26T00:00:00Z", "posture": "TEST"})

    write_json(
        out_ops / "grant_dashboard_status_feed_latest.json",
        {
            "posture": "LOCAL_READY_PORTAL_BLOCKED",
            "summary": {"submitted_by_feed": 0, "local_blockers": 0, "portal_user_blockers": 1},
            "priority_cards": [{"key": "Live Proof Gate", "value": "2/5", "sub": "proposal-specific proof", "tone": "warn"}],
        },
    )
    write_json(
        out_ops / "top5_live_proof_submission_board_latest.json",
        {
            "active_start_package": {"package": "DICE", "portal": "DARPA BAAT"},
            "closest_action_gate": {"portal": "DARPA", "action": "capture final portal facts"},
        },
    )
    write_json(out_ops / "grant_deadline_triage_latest.json", {"summary": {"ready": 1}})
    write_json(
        out_ops / "geometry_proof_frontier_board_latest.json",
        {
            "registry_health": {"family_count": 140},
            "champion_board": {
                "generated_benchmark_champion": {
                    "family": "brachistochrone_descent",
                    "lane": "optimal_curve_transport",
                    "status": "winner",
                },
                "proof_value_champion": {
                    "family": "crack_propagation_paths",
                    "lane": "live_breadth",
                    "proof_priority_score": 91,
                },
                "recommended_next_live_wiring": {"family": "kuramoto_phase_coupling"},
            },
            "promotion_gate": {
                "ready_for_live_geometry_claim": False,
                "ready_for_real_dollar_claim": False,
                "kraken_live_execution_allowed": False,
            },
        },
    )
    write_json(
        out_ops / "geometry_live_breadth_proof_queue_latest.json",
        {
            "schema": "geometry_live_breadth_proof_queue_v1",
            "champions": {
                "fastest_live_breadth_adapter": {
                    "family_id": "crack_propagation_paths",
                    "lane": "ais_review_burden",
                }
            },
            "promotion_gate": {"families_ranked": 140, "ready_for_real_dollar_claim": False},
            "valuation_posture": {"safe_estimated_annual_value_usd": 39595200},
            "top_next_runs": [{"family_id": "kuramoto_phase_coupling"}],
        },
    )
    write_json(
        out_ops / "geometry_asset_wiring_board_latest.json",
        {
            "summary": {
                "field_validation_target_count": 10,
                "buyer_authorized_replay_ready_count": 9,
                "field_validation": False,
            },
            "evidence_boundary": "Asset wiring only. No field validation or realized savings claim.",
            "field_validation_target_queue": [
                {
                    "rank": 1,
                    "family_id": "kuramoto_phase_coupling",
                    "acceptance_gate": "20 buyer-authorized holdout windows beat the locked baseline",
                    "field_validation_claim_allowed_now": False,
                }
            ],
        },
    )
    write_json(out_ops / "local_icloud_evidence_intake_latest.json", {"summary": {"records": 4001}})

    audit = module.build_audit(check_live_domain=False)
    return module, audit


def test_audit_captures_dirty_worktree_as_worktrail_not_trash(audit_fixture):
    _, audit = audit_fixture

    assert audit["schema"] == "luma_context_dashboard_parity_audit_v1"
    dirty = audit["dirty_worktree"]
    assert dirty["total_dirty_entries"] > 0
    assert "active worktrail" in dirty["policy"]
    assert "Do not reset" in dirty["policy"]
    assert "worktrail" in audit["answer_to_why_dirty"]
    assert "unlimited chat memory" in audit["answer_to_context_loss"]
    assert "classify_dirty_worktrail_before_commit" in audit["priority_needs"]


def test_audit_finds_context_checkpoints_and_worktrail_inventory(audit_fixture):
    _, audit = audit_fixture

    checkpoints = {row["key"]: row for row in audit["context_checkpoints"]}
    assert checkpoints["agent_continuity_rules"]["exists"] is True
    assert checkpoints["operating_memory"]["exists"] is True
    assert checkpoints["top5_live_proof_board"]["exists"] is True
    assert checkpoints["geometry_frontier"]["exists"] is True
    assert checkpoints["geometry_live_breadth_queue"]["exists"] is True
    assert checkpoints["local_icloud_intake"]["exists"] is True

    intake = audit["local_icloud_evidence_intake"]
    assert intake["available"] is True
    assert intake["summary"]["records"] >= 4000
    assert "metadata/provenance" in intake["boundary"]


def test_audit_scores_top_dashboards_and_local_feeds_without_domain_claim(audit_fixture):
    _, audit = audit_fixture

    dashboards = {row["key"]: row for row in audit["canonical_dashboards"]}
    assert {"mission_control", "quant_lab", "grants", "proof_to_pilot"}.issubset(dashboards)
    assert dashboards["mission_control"]["references"]["command_fabric_js"] is True
    assert dashboards["mission_control"]["references"]["context_parity_audit"] is True
    assert dashboards["mission_control"]["missing_or_weak_lanes"] == []
    assert dashboards["grants"]["references"]["grant_readiness_status"] is True
    assert dashboards["grants"]["references"]["top5_live_proof"] is True
    assert dashboards["grants"]["references"]["geometry_asset_wiring_board"] is True
    assert dashboards["grants"]["references"]["field_validation_targets"] is True
    assert dashboards["grants"]["references"]["discarded_workspaces"] is True
    assert dashboards["quant_lab"]["references"]["command_fabric_js"] is True
    assert dashboards["quant_lab"]["references"]["context_parity_audit"] is True
    assert dashboards["quant_lab"]["references"]["geometry_frontier"] is True
    assert dashboards["proof_to_pilot"]["references"]["proof_to_pilot_control_room"] is True
    assert dashboards["proof_to_pilot"]["references"]["field_validation_control_room"] is True
    assert dashboards["proof_to_pilot"]["references"]["field_validation_outreach_board"] is True
    assert dashboards["proof_to_pilot"]["missing_or_weak_lanes"] == []

    feeds = {row["key"]: row for row in audit["local_dashboard_feeds"]}
    assert feeds["grant_readiness_status"]["exists"] is True
    assert feeds["top5_live_proof_submission_board"]["exists"] is True
    assert feeds["geometry_asset_wiring_board"]["exists"] is True
    assert feeds["geometry_proof_frontier_board"]["exists"] is True
    assert feeds["geometry_live_breadth_proof_queue"]["exists"] is True
    assert feeds["champion_metric_gauntlet"]["exists"] is True
    assert feeds["field_validation_control_room"]["exists"] is True
    assert feeds["field_validation_outreach_board"]["exists"] is True
    assert feeds["proof_to_pilot_control_room"]["exists"] is True
    assert audit["live_domain_parity"]["checked"] is False
    assert audit["live_domain_parity"]["parity_state"] == "NOT_CHECKED"


def test_audit_keeps_grants_geometry_and_kraken_boundaries_separate(audit_fixture):
    module, audit = audit_fixture

    grant = audit["grant_pipeline"]
    assert grant["dashboard_posture"] == "LOCAL_READY_PORTAL_BLOCKED"
    assert grant["summary"]["submitted_by_feed"] == 0
    assert grant["live_proof_gate"]["value"] == "2/5"
    assert "No final grant submit" in grant["rule"]
    assert grant["active_start_package"]["package"] == "DICE"

    geometry = audit["geometry_frontier"]
    champions = geometry["champions"]
    assert champions["generated_benchmark_champion"]["family"] == "brachistochrone_descent"
    assert champions["proof_value_champion"]["family"] == "crack_propagation_paths"
    gate = geometry["promotion_gate"]
    assert gate["ready_for_live_geometry_claim"] is False
    assert gate["ready_for_real_dollar_claim"] is False
    assert gate["kraken_live_execution_allowed"] is False
    live_queue = geometry["live_breadth_queue"]
    assert live_queue["families_ranked"] >= 75
    assert live_queue["champions"]["fastest_live_breadth_adapter"]["family_id"] == "crack_propagation_paths"
    assert live_queue["promotion_gate"]["ready_for_real_dollar_claim"] is False
    field_targets = geometry["field_validation_targets"]
    field_summary = field_targets["summary"]
    assert field_summary["field_validation_target_count"] >= 10
    assert field_summary["field_validation"] is False
    assert field_targets["top_targets"][0]["family_id"] == "kuramoto_phase_coupling"
    assert field_targets["top_targets"][0]["field_validation_claim_allowed_now"] is False

    rendered = module.render_markdown(audit)
    assert "Live proof gate: `2/5`" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "Kraken live execution allowed: `false`" in rendered
    assert f"Live-breadth queue families ranked: `{live_queue['families_ranked']}`" in rendered
    assert "geometry_asset=true" in rendered
    assert "proof_to_pilot=true" in rendered
    assert "field_control=true" in rendered
    assert "field_outreach=true" in rendered
    assert "Field-validation targets mapped:" in rendered
    assert "guaranteed profit" not in json.dumps(audit).lower()
