from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_OUTREACH_RESPONSE_TEMPLATE_REGISTRY.py"
)
HANDOFF_SCRIPT = (
    ROOT / "code" / "ops" / "EVALUATE_OUTREACH_DISPATCH_HANDOFF.py"
)


def load_registry():
    spec = importlib.util.spec_from_file_location(
        "outreach_response_registry_handoff_test",
        REGISTRY_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def mailbox_receipt(binding: dict[str, object]) -> dict[str, object]:
    checked_utc = "2026-07-27T22:04:55Z"
    return {
        "attachment_count": binding["attachment_count"],
        "attachment_set_sha256": binding["attachment_set_sha256"],
        "bcc_count": 0,
        "body_sha256": binding["body_sha256"],
        "cc_count": 0,
        "checked_utc": checked_utc,
        "current_draft_only": True,
        "draft_present": True,
        "draft_readback_checked_utc": checked_utc,
        "draft_sent": False,
        "full_mailbox_search_completed": True,
        "identifiers_omitted": True,
        "matching_current_draft_count": 1,
        "matching_received_after_draft_count": 0,
        "matching_sent_count": 0,
        "message_body_omitted": True,
        "recipient_route_sha256": binding["recipient_route_sha256"],
        "schema": "lumencore.outreach_action_time_mailbox_receipt.v1",
        "search_scope": "ALL_MAIL_BOUND_ROUTE_THREAD_SUBJECT_BODY",
        "source_message_id_sha256": binding["source_message_id_sha256"],
        "subject_sha256": binding["subject_sha256"],
    }


def build_authorization():
    module = load_registry()
    facts = {
        "recipient_name": "Reviewer",
        "recipient_email": "reviewer@example.org",
        "source_message_id": "synthetic-message-id",
        "source_subject": "Requested information",
        "sender_name": "Founder",
        "sender_title": "Founder / Systems Architect",
        "organization_name": "LumenCore",
        "requested_information": "One bounded technical-review summary.",
    }
    rendered = module.render_response("REQUESTED_INFORMATION_REPLY", facts)
    authorization = module.build_action_time_authorization(
        rendered,
        mailbox_receipt(rendered["dispatch_binding"]),
        current_utc="2026-07-27T22:05:00Z",
    )
    return module, authorization


def run_handoff(
    authorization_path: Path,
    *,
    phrase: str,
    token: str | None,
    expected_sha256: str,
    consumed: bool = False,
    consumption_directory: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LUMA_OUTREACH_EXACT_APPROVAL_PHRASE"] = phrase
    env["LUMA_HUMAN_UNLOCK_SHA256"] = expected_sha256
    if token is None:
        env.pop("LUMA_HUMAN_UNLOCK_TOKEN", None)
    else:
        env["LUMA_HUMAN_UNLOCK_TOKEN"] = token
    directory = (
        consumption_directory
        if consumption_directory is not None
        else authorization_path.parent / "consumption"
    )
    directory.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(HANDOFF_SCRIPT),
        "--authorization",
        str(authorization_path),
        "--consumption-directory",
        str(directory),
        "--current-utc",
        "2026-07-27T22:09:59Z",
    ]
    if consumed:
        command.append("--dispatch-consumed")
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_requires_private_unlock_and_never_exposes_private_inputs(tmp_path):
    module, authorization = build_authorization()
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(
        json.dumps(authorization),
        encoding="utf-8",
    )
    phrase = authorization["exact_action_time_approval_phrase"]
    token = "synthetic-private-unlock"
    expected_sha256 = module.sha256_bytes(token.encode("utf-8"))

    allowed = run_handoff(
        authorization_path,
        phrase=phrase,
        token=token,
        expected_sha256=expected_sha256,
    )
    assert allowed.returncode == 0, allowed.stderr
    receipt = json.loads(allowed.stdout)
    assert receipt["dispatch_authorized"] is True
    assert receipt["send_authorized"] is True
    assert receipt["send_performed"] is False
    assert receipt["external_action_performed"] is False
    assert receipt["private_inputs_omitted"] is True
    assert receipt["consumption_directory_checked"] is True
    assert receipt["consumption_receipt_present"] is False
    assert phrase not in allowed.stdout
    assert token not in allowed.stdout
    assert expected_sha256 not in allowed.stdout

    missing = run_handoff(
        authorization_path,
        phrase=phrase,
        token=None,
        expected_sha256=expected_sha256,
    )
    assert missing.returncode == 3, missing.stderr
    blocked = json.loads(missing.stdout)
    assert blocked["action_time_approval_valid"] is True
    assert blocked["private_human_unlock_valid"] is False
    assert blocked["dispatch_authorized"] is False
    assert blocked["send_authorized"] is False
    assert blocked["blockers"] == [
        "PRIVATE_HUMAN_UNLOCK_TOKEN_REQUIRED"
    ]
    assert phrase not in missing.stdout
    assert token not in missing.stdout
    assert expected_sha256 not in missing.stdout


def test_cli_fails_closed_after_single_use_binding_is_consumed(tmp_path):
    module, authorization = build_authorization()
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(
        json.dumps(authorization),
        encoding="utf-8",
    )
    phrase = authorization["exact_action_time_approval_phrase"]
    token = "synthetic-private-unlock"
    result = run_handoff(
        authorization_path,
        phrase=phrase,
        token=token,
        expected_sha256=module.sha256_bytes(token.encode("utf-8")),
        consumed=True,
    )

    assert result.returncode == 3, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["private_human_unlock_valid"] is True
    assert receipt["dispatch_authorized"] is False
    assert receipt["send_performed"] is False
    assert "SINGLE_USE_BINDING_ALREADY_CONSUMED" in receipt["blockers"]


def test_cli_blocks_when_deterministic_consumption_receipt_exists(tmp_path):
    module, authorization = build_authorization()
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(
        json.dumps(authorization),
        encoding="utf-8",
    )
    consumption_directory = tmp_path / "consumption"
    consumption_directory.mkdir()
    binding_sha256 = authorization["dispatch_binding"]["binding_sha256"]
    (consumption_directory / f"{binding_sha256}.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    token = "synthetic-private-unlock"

    result = run_handoff(
        authorization_path,
        phrase=authorization["exact_action_time_approval_phrase"],
        token=token,
        expected_sha256=module.sha256_bytes(token.encode("utf-8")),
        consumption_directory=consumption_directory,
    )

    assert result.returncode == 3, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["consumption_directory_checked"] is True
    assert receipt["consumption_receipt_present"] is True
    assert receipt["single_use_binding_consumed"] is True
    assert receipt["dispatch_authorized"] is False
    assert "SINGLE_USE_BINDING_ALREADY_CONSUMED" in receipt["blockers"]
