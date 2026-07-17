import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL.py"
JSON_OUT = (
    ROOT
    / "grant_submissions"
    / "OPENAI_BUILD_WEEK_20260721"
    / "BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_week_handoff_integrity_control", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_handoff_control_is_deterministic_and_fail_closed():
    module = load_module()
    expected = module.build_payload()
    actual = json.loads(JSON_OUT.read_text(encoding="utf-8"))

    module.validate_payload(actual)
    assert actual == expected
    assert actual["status"] == (
        "REFERENCED_HANDOFF_UNAVAILABLE_EXECUTION_SCOPE_BOUNDED"
    )
    assert actual["integrity_findings"]["gmail_attachment_count"] == 0
    assert actual["integrity_findings"]["full_handoff_body_available"] is False
    assert actual["integrity_findings"]["embedded_rule_count"] == 10
    assert actual["execution_control"]["may_claim_full_handoff_read"] is False
    assert actual["execution_control"]["may_infer_missing_instructions"] is False
    assert actual["execution_control"]["may_stage_all_paths"] is False
    assert actual["execution_control"]["may_send_email"] is False
    assert actual["execution_control"]["may_submit_devpost"] is False


def test_handoff_control_preserves_available_rules_and_missing_scope():
    module = load_module()
    payload = module.build_payload()
    rules = payload["available_authoritative_rules"]

    assert any("git add -A" in rule for rule in rules)
    assert any("1578504204c429d7f05779897dc3d5430038f681" in rule for rule in rules)
    assert any("Evidence Lattice" in rule for rule in rules)
    assert any("Do not submit Devpost" in rule for rule in rules)
    assert "Evidence Lattice visual design and acceptance criteria" in payload[
        "unavailable_instruction_scope"
    ]
    assert "must not be invented" in payload["control_boundary"]


def test_public_handoff_control_excludes_private_mailbox_data():
    module = load_module()
    rendered = json.dumps(module.build_payload(), sort_keys=True).lower()

    for forbidden in (
        "@gmail.com",
        "message_id",
        "thread_id",
        "raw_mime_base64url",
        "c:\\users\\",
        "client_secret",
        "refresh_token",
        "api_key",
    ):
        assert forbidden not in rendered
