from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_ENGAGEMENT_CLOCK_GATE.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EXTERNAL_ENGAGEMENT_CLOCK_GATE_E_DRIVE_SYNC_RECEIPT_2026-07-16.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("external_engagement_clock_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def live_receipt_fixture(module, retrieved_utc: str = "2026-07-17T04:30:00Z"):
    receipt = json.loads(module.NASHVILLE_LIVE_RECEIPT.read_text(encoding="utf-8"))
    receipt["retrieved_utc"] = retrieved_utc
    receipt["generated_utc"] = retrieved_utc
    receipt.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = module.stable_hash(receipt)
    return receipt


def test_clock_gate_identifies_only_the_immediate_human_fact_lane():
    module = load_module()
    register = json.loads(module.REGISTER.read_text(encoding="utf-8"))
    payload = module.build_payload(
        as_of_utc="2026-07-17T04:57:00Z",
        generated_utc="2026-07-17T04:57:00Z",
        nashville_live_receipt=live_receipt_fixture(module),
    )
    controls = {row["lane_id"]: row for row in payload["controls"]}

    assert payload["schema"] == "lumencore.external_engagement_clock_gate.v1"
    assert payload["status"] == "HUMAN_ACTION_DUE_NO_AUTONOMOUS_SEND"
    assert payload["summary"]["lane_count"] == len(register["records"])
    assert payload["summary"]["immediate_human_action_count"] == 1
    assert payload["summary"]["date_only_deadline_count"] == sum(
        1
        for row in register["records"]
        if row.get("deadline") and "T" not in row["deadline"]
    )
    assert payload["summary"]["duplicate_send_block_count"] == sum(
        1 for row in register["records"] if row.get("do_not_duplicate_send")
    )
    assert payload["summary"]["active_follow_up_hold_count"] == 2
    assert payload["summary"]["autonomous_external_send_allowed"] is False
    assert payload["summary"]["autonomous_final_submit_allowed"] is False
    assert payload["summary"]["browser_navigation_performed"] is False
    assert payload["summary"]["nashville_live_receipt_hash_valid"] is True
    assert payload["summary"][
        "nashville_official_deadline_confirmation_verified"
    ] is True
    assert payload["summary"][
        "nashville_official_deadline_sentence_hash_valid"
    ] is True
    assert payload["summary"]["nashville_official_live_source_verified"] is True

    nashville = controls["nashville_ec_takeoff_fall_2026"]
    assert nashville["priority"] == "P0_HUMAN_FACTS_NOW"
    assert nashville["human_fact_gate_open"] is True
    assert nashville["human_action_required_now"] is True
    assert nashville["deadline_precision"] == "TIMESTAMP_WITH_TIMEZONE"
    assert nashville["deadline_state"] == "UNDER_72_HOURS"
    assert nashville["hours_remaining"] == 24.03
    assert nashville["official_deadline_confirmation_verified"] is True
    assert nashville["deadline_timezone_explicit_in_message"] is False
    assert nashville["operational_timezone"] == "America/Chicago"
    assert nashville["official_live_source_gate"] == "VERIFIED_CURRENT"
    assert nashville["official_open_signals_verified"] is True
    assert nashville["official_live_source_fresh"] is True
    assert controls["launchtn_3686_pitch_2026"]["human_fact_gate_open"] is True
    assert controls["launchtn_3686_pitch_2026"]["human_action_required_now"] is False
    assert controls["sam_public_credential_rotation"]["human_fact_gate_open"] is False


def test_clock_gate_blocks_duplicate_outreach_and_preserves_holds():
    module = load_module()
    register = json.loads(module.REGISTER.read_text(encoding="utf-8"))
    payload = module.build_payload(
        as_of_utc="2026-07-17T04:57:00Z",
        generated_utc="2026-07-17T04:57:00Z",
        nashville_live_receipt=live_receipt_fixture(module),
    )
    controls = {row["lane_id"]: row for row in payload["controls"]}

    for source_row in register["records"]:
        row = controls[source_row["lane_id"]]
        expected = (
            "BLOCKED_DO_NOT_DUPLICATE"
            if source_row.get("do_not_duplicate_send")
            else "NOT_APPLICABLE"
        )
        assert row["duplicate_send_control"] == expected
        if source_row.get("do_not_duplicate_send"):
            assert row["autonomous_external_send_allowed"] is False
            assert row["autonomous_final_submit_allowed"] is False

    for lane_id in (
        "epri_open_power_ai_mou",
        "lanl_vision_licensing_followup",
    ):
        assert controls[lane_id]["follow_up_hold_state"] == "FOLLOW_UP_HOLD_ACTIVE"

    assert controls["georgia_patents_pro_bono_intake"]["follow_up_hold_state"] == (
        "NO_HOLD_RECORDED"
    )
    assert controls["fhwa_tsmo_qualified_partner_outreach"]["follow_up_hold_state"] == (
        "NO_HOLD_RECORDED"
    )

    assert controls["nasa_data_center_rfi"]["deadline_state"] == "UNDER_24_HOURS"
    assert controls["nasa_data_center_rfi"]["priority"] == "P2_MONITOR_NO_DUPLICATE"


def test_clock_gate_verifies_source_and_record_hashes():
    module = load_module()
    register = json.loads(module.REGISTER.read_text(encoding="utf-8"))
    payload = module.build_payload(
        as_of_utc="2026-07-17T04:57:00Z",
        generated_utc="2026-07-17T04:57:00Z",
        nashville_live_receipt=live_receipt_fixture(module),
    )

    assert payload["summary"]["source_register_hash_valid"] is True
    assert payload["summary"]["all_record_hashes_valid"] is True
    assert payload["summary"]["verified_record_hash_count"] == len(register["records"])
    assert len(payload["source"]["sha256"]) == 64
    assert payload["source"]["nashville_live_deadline_receipt"]["receipt_hash_valid"] is True
    assert len(payload["gate_sha256"]) == 64
    for row in payload["controls"]:
        assert row["record_hash_valid"] is True
        assert len(row["control_sha256"]) == 64


def test_rendered_gate_is_public_safe_and_claim_bounded():
    module = load_module()
    payload = module.build_payload(
        as_of_utc="2026-07-17T04:57:00Z",
        generated_utc="2026-07-17T04:57:00Z",
        nashville_live_receipt=live_receipt_fixture(module),
    )
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    module.ensure_public_safe(rendered)
    assert "only immediate human-fact action" in lowered
    assert "official ec email confirms an 11:59 p.m. july 17 close" in lowered
    assert "operational inference" in lowered
    assert "nashville official deadline confirmation verified: `true`" in lowered
    assert "nashville official live source verified: `true`" in lowered
    assert "session-browser navigation performed: `false`" in lowered
    assert "does not establish" in lowered
    for marker in module.PRIVATE_MARKERS:
        assert marker not in lowered


def test_stale_page_receipt_does_not_override_verified_email_deadline():
    module = load_module()
    payload = module.build_payload(
        as_of_utc="2026-07-17T12:00:00Z",
        generated_utc="2026-07-17T12:00:00Z",
        nashville_live_receipt=live_receipt_fixture(
            module, retrieved_utc="2026-07-17T04:30:00Z"
        ),
    )
    nashville = next(
        row
        for row in payload["controls"]
        if row["lane_id"] == "nashville_ec_takeoff_fall_2026"
    )

    assert payload["status"] == "HUMAN_ACTION_DUE_NO_AUTONOMOUS_SEND"
    assert payload["summary"]["nashville_official_live_source_verified"] is False
    assert payload["summary"][
        "nashville_official_deadline_confirmation_verified"
    ] is True
    assert "does not override the verified email deadline" in payload["direct_answer"]
    assert nashville["official_live_source_gate"] == "REVERIFY_REQUIRED"
    assert nashville["official_live_source_fresh"] is False
    assert nashville["official_live_source_age_hours"] == 7.5


def test_bounded_e_drive_mirror_matches_every_clock_gate_artifact():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8-sig"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 6
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    for artifact in receipt["artifacts"]:
        mirror = Path(artifact["destination"])
        source = Path(artifact["source"])
        assert source.is_absolute() is False
        assert ".." not in source.parts
        assert mirror.is_file(), artifact["destination"]
        assert mirror.stat().st_size == artifact["bytes"]
        mirror_hash = hashlib.sha256(mirror.read_bytes()).hexdigest().upper()
        assert mirror_hash == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    assert "does not prove email transmission" in receipt["claim_boundary"]
