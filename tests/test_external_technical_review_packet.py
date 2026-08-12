from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_TECHNICAL_REVIEW_PACKET.py"
CONFIG = ROOT / "config" / "external_technical_review_packet_v1.json"
JSON_OUT = ROOT / "dashboard" / "data" / "external_technical_review_packet.json"
MD_OUT = ROOT / "docs" / "EXTERNAL_TECHNICAL_REVIEW_PACKET_2026-07-28.md"


def load_module():
    spec = importlib.util.spec_from_file_location("external_review_packet", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_packet_is_no_send_and_no_duplicate():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))

    assert payload["status"] == "MEETING_PREP_READY_NO_DUPLICATE_SEND"
    assert payload["meeting"]["invite_state"] == "ACCEPTED"
    assert payload["meeting"]["selected_template_id"] == (
        "NO_DUPLICATE_MEETING_PREP"
    )
    assert payload["controls"]["builder_can_send_email"] is False
    assert payload["controls"]["builder_can_create_calendar_event"] is False
    assert payload["controls"]["duplicate_invite_prohibited"] is True
    assert payload["summary"]["duplicate_invite_blocked"] is True


def test_every_evidence_asset_exists_and_is_hash_bound():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))

    assert payload["summary"]["evidence_asset_count"] == 11
    for row in payload["evidence_assets"]:
        assert len(row["sha256"]) == 64
        assert row["bytes"] > 0
        if row["required_status"]:
            assert row["observed_status"] == row["required_status"]
            assert row["claim_boundary"]


def test_text_evidence_digest_and_size_are_line_ending_stable(tmp_path):
    module = load_module()
    lf_path = tmp_path / "lf.txt"
    crlf_path = tmp_path / "crlf.txt"
    lf_path.write_bytes(b"alpha\nbeta\n")
    crlf_path.write_bytes(b"alpha\r\nbeta\r\n")

    assert module.canonical_file_bytes(lf_path) == b"alpha\nbeta\n"
    assert module.canonical_file_bytes(crlf_path) == b"alpha\nbeta\n"
    assert module.sha256_file(lf_path) == module.sha256_file(crlf_path)
    assert len(module.canonical_file_bytes(lf_path)) == len(
        module.canonical_file_bytes(crlf_path)
    )


def test_public_snapshot_uses_only_current_bounded_contract_surfaces():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))
    by_label = {row["label"]: row for row in payload["public_surfaces"]}
    urls = {row["url"] for row in payload["public_surfaces"]}

    assert payload["summary"]["public_surface_count"] == 7
    assert payload["summary"]["demo_surface_count"] == 1
    assert payload["summary"]["degraded_surface_count"] == 0
    assert by_label["Dynamic health endpoint"]["observed_http_status"] == 200
    assert by_label["Public status endpoint"]["observed_http_status"] == 200
    assert by_label["Dynamic health endpoint"]["required_json"]["status"] == "ok"
    assert by_label["External replication docket"]["required_text"] == (
        "External replication docket v1"
    )
    assert all(row["url"].startswith("https://") for row in by_label.values())
    assert "https://lumen-core.ai/mission_control.html" not in urls
    assert "https://lumen-core.ai/grants.html" not in urls


def test_packet_rejects_retired_public_surfaces():
    module = load_module()
    config = module.read_json(CONFIG)

    for path in module.RETIRED_PUBLIC_SURFACE_PATHS:
        retired = copy.deepcopy(config)
        retired["public_surfaces"].append(
            copy.deepcopy(retired["public_surfaces"][0])
        )
        retired["public_surfaces"][-1]["url"] = f"https://lumen-core.ai{path}"

        with pytest.raises(module.ReviewPacketError, match="RETIRED_PUBLIC_SURFACE:"):
            module.build_payload(retired)


def test_live_surface_verification_accepts_the_exact_bounded_snapshot(monkeypatch):
    module = load_module()
    config = module.read_json(CONFIG)
    expected = {
        row["url"]: {
            "observed_status": row["observed_http_status"],
            "observed_content_type": row["expected_content_type"],
            "content_type_match": True,
            "contract_match": True,
        }
        for row in config["public_surfaces"]
    }
    monkeypatch.setattr(
        module, "observe_public_surface", lambda row: expected[row["url"]]
    )

    observed = module.verify_live_surfaces(config)

    assert len(observed) == len(expected)
    assert all(row["match"] for row in observed)


def test_live_surface_verification_fails_closed_on_status_drift(monkeypatch):
    module = load_module()
    config = module.read_json(CONFIG)
    expected = {
        row["url"]: {
            "observed_status": row["observed_http_status"],
            "observed_content_type": row["expected_content_type"],
            "content_type_match": True,
            "contract_match": True,
        }
        for row in config["public_surfaces"]
    }
    drift_url = config["public_surfaces"][0]["url"]
    expected[drift_url]["observed_status"] = 503
    monkeypatch.setattr(
        module,
        "observe_public_surface",
        lambda row: expected[row["url"]],
    )

    try:
        module.verify_live_surfaces(config)
    except module.ReviewPacketError as exc:
        assert str(exc).startswith("LIVE_SURFACE_CONTRACT_DRIFT:")
        assert f"{drift_url}=503" in str(exc)
    else:
        raise AssertionError("live status drift must fail closed")


def test_live_surface_verification_fails_closed_on_content_drift(monkeypatch):
    module = load_module()
    config = module.read_json(CONFIG)
    drift_url = config["public_surfaces"][0]["url"]

    def observation(row):
        return {
            "observed_status": row["observed_http_status"],
            "observed_content_type": row["expected_content_type"],
            "content_type_match": True,
            "contract_match": row["url"] != drift_url,
        }

    monkeypatch.setattr(module, "observe_public_surface", observation)

    with pytest.raises(
        module.ReviewPacketError,
        match=r"LIVE_SURFACE_CONTRACT_DRIFT:.*contract=false",
    ):
        module.verify_live_surfaces(config)


def test_packet_keeps_historical_and_external_evidence_boundaries_explicit():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))
    markdown = module.render_markdown(payload)
    reference = payload["draft_references"][0]

    assert reference["state"] == "CLOSED_UNMERGED"
    assert "closed without merge" in reference["use"]
    assert "superseded by merged PR #132" in reference["use"]
    assert "Do not use it as packet evidence" in reference["use"]
    assert "not independent external validation" in markdown
    assert "branch-only contents are excluded" in markdown
    assert "does not establish attendance" in markdown
    assert "Do not send another reply or invitation" in markdown
    assert "meeting link" not in markdown.lower()
    assert "recipient_name" not in markdown


def test_packet_reconciles_named_static_release_without_broadening_claims():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))
    markdown = module.render_markdown(payload)
    evidence_paths = {row["path"] for row in payload["evidence_assets"]}

    assert (
        "evidence/public-site-deployments/"
        "1ce7c35975a4011fa844e8b39ccbc950c8c0f398/deployment-receipt.json"
        in evidence_paths
    )
    assert "43 allowlisted files" in markdown
    assert "exact live-byte matches" in markdown
    assert "exact-snapshot static release parity remains unreconciled" not in markdown
    assert "does not establish external validation" in markdown
    assert "runtime parity" in markdown
    assert "broader production authorization" in markdown


def test_reviewer_questions_force_buyer_baseline_metric_and_negative_result_path():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))
    questions = " ".join(payload["reviewer_questions"]).lower()
    next_steps = " ".join(payload["bounded_next_steps"]).lower()

    assert "buyer" in questions
    assert "baseline" in questions
    assert "acceptance metric" in questions
    assert "independent evaluator" in questions
    assert "no fit" in next_steps


def test_assurance_exercise_is_bounded_hash_bound_and_replayable():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))
    exercise = payload["assurance_exercise"]

    assert exercise["mode"] == "REVIEWER_CONTROLLED_LOCAL_REPLAY_ONLY"
    assert payload["summary"]["assurance_scenario_count"] == 6
    assert payload["summary"]["active_targeting_allowed"] is False
    assert set(exercise["roles"]) == {"red_team", "blue_team", "purple_team"}
    assert all(value is False for value in exercise["authority_boundary"].values())

    scenario_ids = [row["scenario_id"] for row in exercise["scenarios"]]
    assert len(scenario_ids) == len(set(scenario_ids))
    for row in exercise["scenarios"]:
        test_path = ROOT / row["test_path"]
        assert test_path.is_file()
        assert row["verification_command"] == (
            f"python -m pytest -q {row['test_path']}"
        )
        assert row["test_sha256"] == module.sha256_file(test_path)
        assert row["test_bytes"] == len(module.canonical_file_bytes(test_path))
        assert len(row["boundary"]) > 40

    markdown = module.render_markdown(payload)
    assert "Reviewer-Controlled Red / Blue Assurance Exercise" in markdown
    assert "Active targeting" in markdown
    assert "Purple team" in markdown
    assert "does not establish penetration testing" in markdown


def test_assurance_exercise_rejects_active_targeting_or_duplicate_scenarios():
    module = load_module()
    config = module.read_json(CONFIG)

    active = copy.deepcopy(config)
    active["assurance_exercise"]["authority_boundary"][
        "active_targeting_allowed"
    ] = True
    with pytest.raises(
        module.ReviewPacketError,
        match="ASSURANCE_AUTHORITY_BOUNDARY_INVALID",
    ):
        module.build_payload(active)

    duplicate = copy.deepcopy(config)
    duplicate["assurance_exercise"]["scenarios"][1]["scenario_id"] = duplicate[
        "assurance_exercise"
    ]["scenarios"][0]["scenario_id"]
    with pytest.raises(
        module.ReviewPacketError,
        match="ASSURANCE_SCENARIO_ID_INVALID",
    ):
        module.build_payload(duplicate)


def test_written_outputs_match_the_builder():
    module = load_module()
    expected = module.build_payload(module.read_json(CONFIG))

    assert json.loads(JSON_OUT.read_text(encoding="utf-8")) == expected
    assert MD_OUT.read_text(encoding="utf-8") == module.render_markdown(expected)
