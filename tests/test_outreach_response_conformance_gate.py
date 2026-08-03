from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_OUTREACH_RESPONSE_CONFORMANCE_GATE.py"
CONFIG = ROOT / "config" / "outreach_response_conformance_v1.json"
AS_OF_UTC = "2026-07-26T22:45:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("outreach_conformance", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def load_payloads(config: dict) -> dict[str, dict]:
    return {
        material_id: json.loads((ROOT / material["path"]).read_text(encoding="utf-8"))
        for material_id, material in config["materials"].items()
    }


def write_override(tmp_path: Path, payload: dict, name: str) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path.as_posix()


def test_config_is_fail_closed_and_material_set_is_complete():
    module = load_module()
    config = load_config()
    module.validate_config(config)

    assert config["controls"] == module.EXPECTED_CONTROLS
    assert set(config["materials"]) == module.EXPECTED_MATERIALS
    assert config["controls"]["autonomous_email_send_allowed"] is False
    assert config["controls"]["action_time_human_approval_required"] is True


def test_current_gate_has_valid_templates_but_no_releasable_response():
    module = load_module()
    gate = module.build_gate(CONFIG, root=ROOT, as_of_utc=AS_OF_UTC)

    assert gate["status"] == "BLOCKED_NO_OUTBOUND_RESPONSE_READY"
    assert gate["summary"]["material_count"] == 7
    assert gate["summary"]["material_blocker_count"] == 0
    assert gate["summary"]["template_count"] == 16
    assert gate["summary"]["structurally_valid_template_count"] == 16
    assert gate["summary"]["externally_releasable_template_count"] == 0
    assert gate["summary"]["lane_count"] == 28
    assert gate["summary"]["mailbox_recheck_candidate_count"] == 0
    assert gate["summary"]["draft_render_ready_count"] == 0
    assert gate["summary"]["send_ready_lane_count"] == 0
    assert gate["summary"]["external_action_count"] == 0
    assert gate["blockers"] == []


def test_template_source_config_hash_uses_declared_canonical_basis():
    module = load_module()
    config = load_config()
    registry = load_payloads(config)["response_template_registry"]
    source_path = ROOT / registry["source_config"]

    assert registry["source_config_hash_basis"] == "SORTED_COMPACT_JSON_UTF8"
    assert module.canonical_sha256(module.read_json(source_path)) == (
        registry["source_config_sha256"]
    )
    assert module.file_sha256(source_path) != registry["source_config_sha256"]

    gate = module.build_gate(CONFIG, root=ROOT, as_of_utc=AS_OF_UTC)
    assert all(
        blocker["code"] != "TEMPLATE_SOURCE_CONFIG_DRIFT"
        for blocker in gate["blockers"]
    )


def test_every_lane_template_reference_exists_and_every_send_is_blocked():
    module = load_module()
    gate = module.build_gate(CONFIG, root=ROOT, as_of_utc=AS_OF_UTC)
    template_ids = {
        row["template_id"] for row in gate["template_release_states"]
    }

    for row in gate["lane_release_states"]:
        assert row["send_ready"] is False
        assert row["external_action_allowed"] is False
        if row["current_response_template_id"]:
            assert row["current_response_template_id"] in template_ids
        if row["eligible_template_id"]:
            assert row["eligible_template_id"] in template_ids


def test_queue_hash_drift_is_detected():
    module = load_module()
    config = load_config()
    queue_path = ROOT / config["materials"]["followup_queue"]["path"]
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["status"] = "TAMPERED"
    relative = "tmp/outreach_conformance_hash_drift.json"
    override = ROOT / relative
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    config["materials"]["followup_queue"]["path"] = relative
    config_path = ROOT / "tmp" / "outreach_conformance_hash_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    gate = module.build_gate(config_path, root=ROOT, as_of_utc=AS_OF_UTC)

    assert "QUEUE_SELF_HASH_INVALID" in {
        blocker["code"] for blocker in gate["blockers"]
    }


def test_unknown_template_reference_is_a_blocker(tmp_path: Path):
    module = load_module()
    config = load_config()
    queue_path = ROOT / config["materials"]["followup_queue"]["path"]
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["actions"][0]["eligible_template_id"] = "UNKNOWN_TEMPLATE"
    queue["queue_sha256"] = module.canonical_sha256(
        {key: value for key, value in queue.items() if key != "queue_sha256"}
    )
    relative = "tmp/outreach_conformance_unknown_template.json"
    override = ROOT / relative
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    config["materials"]["followup_queue"]["path"] = relative
    config_path = ROOT / "tmp" / "outreach_conformance_unknown_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    gate = module.build_gate(config_path, root=ROOT, as_of_utc=AS_OF_UTC)

    assert gate["status"] == "BLOCKED_MATERIAL_OR_CONTROL_INTEGRITY"
    assert "UNKNOWN_TEMPLATE_REFERENCE" in {
        blocker["code"] for blocker in gate["blockers"]
    }


def test_nonzero_send_flag_is_a_blocker():
    module = load_module()
    config = load_config()
    queue_path = ROOT / config["materials"]["followup_queue"]["path"]
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["actions"][0]["send_now"] = True
    queue["queue_sha256"] = module.canonical_sha256(
        {key: value for key, value in queue.items() if key != "queue_sha256"}
    )
    relative = "tmp/outreach_conformance_send_now.json"
    override = ROOT / relative
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    config["materials"]["followup_queue"]["path"] = relative
    config_path = ROOT / "tmp" / "outreach_conformance_send_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    gate = module.build_gate(config_path, root=ROOT, as_of_utc=AS_OF_UTC)

    assert "QUEUE_SEND_NOW_NOT_BLOCKED" in {
        blocker["code"] for blocker in gate["blockers"]
    }


def test_relaxed_reviewer_release_gate_is_detected():
    module = load_module()
    config = load_config()
    reviewer_path = ROOT / config["materials"]["reviewer_objection_gate"]["path"]
    reviewer = json.loads(reviewer_path.read_text(encoding="utf-8"))
    reviewer["summary"]["partner_outreach_allowed"] = True
    reviewer["gate_sha256"] = module.canonical_sha256(
        {key: value for key, value in reviewer.items() if key != "gate_sha256"}
    )
    relative = "tmp/outreach_conformance_reviewer_relaxed.json"
    override = ROOT / relative
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(json.dumps(reviewer, indent=2) + "\n", encoding="utf-8")
    config["materials"]["reviewer_objection_gate"]["path"] = relative
    config_path = ROOT / "tmp" / "outreach_conformance_reviewer_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    gate = module.build_gate(config_path, root=ROOT, as_of_utc=AS_OF_UTC)

    assert "REVIEWER_RELEASE_GATE_RELAXED" in {
        blocker["code"] for blocker in gate["blockers"]
    }


def test_output_is_deterministic_public_safe_and_has_no_action_capability():
    module = load_module()
    first = module.build_gate(CONFIG, root=ROOT, as_of_utc=AS_OF_UTC)
    second = module.build_gate(CONFIG, root=ROOT, as_of_utc=AS_OF_UTC)
    document = module.render_markdown(first)

    assert first == second
    expected = copy.deepcopy(first)
    observed_hash = expected.pop("gate_sha256")
    assert observed_hash == module.canonical_sha256(expected)
    assert "no outbound response is currently release-ready" in document
    assert "@" not in document
    assert first["capability_boundary"]["email_send_performed"] is False
    assert first["capability_boundary"]["private_draft_rendered"] is False


def test_private_output_key_is_rejected():
    module = load_module()
    with pytest.raises(module.ConformanceError, match="Private-data key"):
        module._walk_private_keys({"recipient_email": "private@example.invalid"})


def test_builder_source_has_no_network_email_or_browser_client():
    source = SCRIPT.read_text(encoding="utf-8").lower()
    assert "import requests" not in source
    assert "import smtplib" not in source
    assert "import webbrowser" not in source
    assert "import selenium" not in source
    assert "import playwright" not in source
    assert "subprocess" not in source
