from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_OPENAI_BUILD_WEEK_READINESS_PACKET.py"
OUT_DIR = ROOT / "grant_submissions" / "OPENAI_BUILD_WEEK_20260721"


def load_module():
    spec = importlib.util.spec_from_file_location("openai_build_week_readiness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_readiness_packet_uses_official_deadline_and_equal_weight_criteria():
    module = load_module()
    payload = module.build_payload()
    facts = payload["official_requirements"]["facts"]

    assert payload["schema"] == "lumencore.openai_build_week_submission_readiness.v1"
    assert facts["submission_period"]["deadline_pacific"] == "2026-07-21T17:00:00-07:00"
    assert facts["submission_period"]["deadline_central"] == "2026-07-21T19:00:00-05:00"
    assert facts["submission_period"]["deadline_utc"] == "2026-07-22T00:00:00Z"
    assert facts["category"] == "Developer Tools"
    assert facts["judging"]["stage_two_equal_weight_criteria"] == [
        "Technological Implementation",
        "Design",
        "Potential Impact",
        "Quality of the Idea",
    ]
    assert payload["official_requirements"]["official_sources"]["rules"] == (
        "https://openai.devpost.com/rules"
    )


def test_project_core_is_verified_from_post_start_commit_and_sample_receipt():
    module = load_module()
    payload = module.build_payload()

    assert payload["status"] == "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN"
    assert payload["core_ready"] is True
    assert payload["ready_for_final_submission"] is False
    assert payload["new_work_evidence"]["after_submission_start"] is True
    assert len(payload["new_work_evidence"]["commit"]) == 40
    assert payload["new_work_evidence"]["subject"] == "Add Build Week ProofLock Console"
    assert payload["sample_verification"]["integrity_valid"] is True
    assert payload["sample_verification"]["artifact_count"] == 4
    assert payload["sample_verification"]["artifact_hash_match_count"] == 4
    assert payload["sample_verification"]["promotion_allowed"] is False
    assert payload["sample_verification"]["recorded_decision"] == "HOLD"
    assert len(payload["app_artifacts"]) == 6
    assert all(row["present"] and len(row["sha256"]) == 64 for row in payload["app_artifacts"])
    assert payload["public_demo_verification"]["verified"] is True
    assert payload["project"]["public_demo_url"] == (
        "https://lumen-core.ai/build_week/prooflock_console/"
    )


def test_external_and_final_actions_remain_open_and_human_owned():
    module = load_module()
    payload = module.build_payload()
    gates = {row["gate_id"]: row for row in payload["gates"]}

    assert gates["working_project"]["status"] == "PASS"
    assert gates["post_start_new_work"]["status"] == "PASS"
    assert gates["public_repository"]["status"] == "PASS"
    assert gates["relevant_license"]["status"] == "PASS"
    assert gates["public_demo"]["status"] == "PASS"
    for gate_id in (
        "model_provenance",
        "feedback_session",
        "youtube_demo",
        "devpost_registration",
        "final_submission",
    ):
        assert gates[gate_id]["status"] == "OPEN"
    assert gates["final_submission"]["owner"] == "Robert"
    assert payload["counts"] == {"gate_total": 10, "pass": 5, "open": 5, "fail": 0}


def test_generated_packet_is_hashed_and_claim_bounded():
    module = load_module()
    payload = module.build_payload()
    unhashed = dict(payload)
    recorded = unhashed.pop("packet_sha256")

    assert recorded == module.stable_hash(unhashed)
    assert len(recorded) == 64
    assert "does not prove" in payload["claim_boundary"]
    assert "OpenAI endorsement" in payload["claim_boundary"]
    assert payload["project"]["confirmed_model"] is None
    assert payload["project"]["feedback_session_id"] is None
    assert payload["project"]["public_demo_url"] == (
        "https://lumen-core.ai/build_week/prooflock_console/"
    )
    assert payload["project"]["youtube_demo_url"] is None


def test_rendered_outputs_do_not_invent_model_or_submission_state():
    module = load_module()
    payload = module.build_payload()
    markdown = module.render_markdown(payload)
    description = module.render_description(payload)
    demo = module.render_demo_script(payload)

    assert payload["ready_for_final_submission"] is False
    assert payload["packet_sha256"] in markdown
    assert "add the verified GPT-5.6 model label" in description
    assert "do not infer either value" in description
    assert "under three minutes" in demo
    assert "No copyrighted music" in demo
    assert "Do not state that the concept is CAD" in demo
