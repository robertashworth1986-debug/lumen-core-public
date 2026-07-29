from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_SUBMISSION_CONFORMANCE_GATE.py"
REGISTRY = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "SUBMISSION_CONFORMANCE_REGISTRY_2026-07-25.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("submission_conformance_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def lane_index(payload: dict) -> dict[str, dict]:
    return {row["lane_id"]: row for row in payload["lanes"]}


def test_live_registry_covers_current_federal_and_ip_lanes_and_fails_closed():
    module = load_module()
    payload = module.build_gate()
    lanes = lane_index(payload)

    assert payload["schema"] == "lumencore.submission_conformance_gate.v1"
    assert payload["status"] == "SUBMISSION_CONFORMANCE_BLOCKED"
    assert payload["summary"]["current_lane_universe_count"] == 22
    assert payload["summary"]["current_federal_and_ip_lane_count"] == 15
    assert payload["summary"]["registry_lane_count"] == 22
    assert payload["summary"]["missing_current_lane_count"] == 0
    assert payload["summary"]["active_submission_candidate_count"] == 3
    assert payload["summary"]["active_argument_pass_count"] == 0
    assert payload["summary"]["expired_without_verified_submission_count"] == 1
    assert payload["summary"]["technical_no_go_count"] == 1
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert len(payload["gate_sha256"]) == 64

    dice = lanes["darpa_dice_full_submission"]
    assert dice["status"] == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    assert dice["criterion_fail_count"] >= 4
    assert dice["argument_conformance_pass"] is False
    assert dice["independent_red_team_receipt"]["passes"] is False

    missionweave = lanes["dla_missionweave_sbir"]
    assert missionweave["status"] == "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED"
    assert missionweave["submission_candidate_active"] is False
    assert missionweave["argument_conformance_pass"] is False

    falcon = lanes["darpa_falcon_dpa26bz04_dv016"]
    assert falcon["status"] == "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY"
    assert falcon["submission_candidate_active"] is False
    assert falcon["argument_conformance_pass"] is False

    assert lanes["cdc_ai_acquisition_rfi"]["status"] == (
        "MONITOR_ONLY_NO_DUPLICATE_SUBMISSION"
    )

    for lane_id in ("nsf_project_pitch", "launchtn_3686_pitch_2026"):
        assert lanes[lane_id]["status"] == "BLOCKED_UNASSESSED_CRITERIA"
        assert lanes[lane_id]["criterion_unassessed_count"] == 10
        assert lanes[lane_id]["argument_conformance_pass"] is False

    erdc = lanes["erdc_sovereign_cloud_cso"]
    assert erdc["status"] == "BLOCKED_CRITERION_FAILURE"
    assert erdc["criterion_pass_count"] == 3
    assert erdc["criterion_partial_count"] == 5
    assert erdc["criterion_fail_count"] == 2
    assert erdc["criterion_unassessed_count"] == 0
    assert erdc["argument_conformance_pass"] is False


def test_missing_criterion_and_missing_red_team_receipt_cannot_pass():
    module = load_module()
    registry = load_registry()
    erdc = next(
        row
        for row in registry["lanes"]
        if row["lane_id"] == "erdc_sovereign_cloud_cso"
    )
    erdc["official_source"] = (
        "grant_submissions/DICE_HR001126S0010/HR001126S0010_OFFICIAL.pdf"
    )
    erdc["criteria"] = []
    for criterion_id in module.REQUIRED_CRITERIA[:-1]:
        erdc["criteria"].append(
            {
                "criterion_id": criterion_id,
                "state": "PASS",
                "finding": "Fixture pass with a source reference.",
                "missing_evidence": [],
                "source_refs": [
                    {
                        "path": "README.md",
                        "anchor": "Evidence boundary",
                    }
                ],
            }
        )

    payload = module.build_gate(registry=registry)
    lane = lane_index(payload)["erdc_sovereign_cloud_cso"]
    assert lane["criterion_pass_count"] == 9
    assert lane["criterion_unassessed_count"] == 1
    assert lane["argument_conformance_pass"] is False
    assert lane["status"] == "BLOCKED_UNASSESSED_CRITERIA"

    final_criterion = module.REQUIRED_CRITERIA[-1]
    erdc["criteria"].append(
        {
            "criterion_id": final_criterion,
            "state": "PASS",
            "finding": "Fixture pass with a source reference.",
            "missing_evidence": [],
            "source_refs": [{"path": "README.md", "anchor": "Evidence boundary"}],
        }
    )
    payload = module.build_gate(registry=registry)
    lane = lane_index(payload)["erdc_sovereign_cloud_cso"]
    assert lane["criterion_pass_count"] == 10
    assert lane["status"] == "BLOCKED_INDEPENDENT_RED_TEAM_RECEIPT"
    assert lane["argument_conformance_pass"] is False


def test_registry_rejects_self_attested_red_team_receipt():
    module = load_module()
    registry = load_registry()
    erdc = next(
        row
        for row in registry["lanes"]
        if row["lane_id"] == "erdc_sovereign_cloud_cso"
    )
    erdc["independent_red_team_receipt"] = {
        "path": "README.md",
        "reviewer_relation": "PRIMARY_DRAFTER_SELF_ATTESTED",
        "verdict": "PASS",
    }

    with pytest.raises(module.ConformanceError, match="separate reviewer"):
        module.validate_registry(registry)


def test_current_supplemental_sources_are_part_of_coverage():
    module = load_module()
    payload = module.build_gate()

    assert payload["current_lane_sources"]["near_deadline_selected"] == [
        "cdc_ai_acquisition_rfi",
        "dla_missionweave_sbir",
        "erdc_sovereign_cloud_cso",
        "launchtn_3686_pitch_2026",
    ]
    assert payload["current_lane_sources"]["explicit_current_lanes"] == [
        "darpa_falcon_dpa26bz04_dv016"
    ]
    assert payload["current_lane_sources"]["current_public_leads"] == [
        "aws_activate_founders_2026",
        "launchtn_3686_pitch_2026",
        "microsoft_for_startups_no_referral_2026",
        "nvidia_inception_2026",
    ]
    for source_name in (
        "near_deadline",
        "public_leads",
        "falcon_gap_map",
    ):
        assert payload["source_evidence"][source_name]["present"] is True
        assert len(payload["source_evidence"][source_name]["sha256"]) == 64


def test_unknown_current_lane_is_reported_and_blocks_coverage():
    module = load_module()
    traction = json.loads(module.TRACTION_PATH.read_text(encoding="utf-8"))
    extra = copy.deepcopy(traction["lanes"][0])
    extra["lane_id"] = "fixture_unknown_federal_lane"
    extra["channel"] = "federal_baa"
    traction["lanes"].append(extra)

    payload = module.build_gate(traction=traction)
    assert payload["summary"]["missing_current_lane_count"] == 1
    assert payload["missing_current_lane_ids"] == ["fixture_unknown_federal_lane"]
    assert payload["status"] == "SUBMISSION_CONFORMANCE_BLOCKED"


def test_markdown_is_public_safe_and_keeps_human_gate():
    module = load_module()
    payload = module.build_gate()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Submission Conformance Gate" in rendered
    assert "darpa_dice_full_submission" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "password" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
    assert module.scan_sensitive_text(rendered) == []
