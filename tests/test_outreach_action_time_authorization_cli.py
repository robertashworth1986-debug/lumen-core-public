from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_OUTREACH_RESPONSE_TEMPLATE_REGISTRY.py"
)
AUTHORIZATION_SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_OUTREACH_ACTION_TIME_AUTHORIZATION.py"
)


def load_registry():
    spec = importlib.util.spec_from_file_location(
        "outreach_response_registry_authorization_cli_test",
        REGISTRY_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ready_inputs() -> tuple[dict[str, object], dict[str, object]]:
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
    binding = rendered["dispatch_binding"]
    checked_utc = datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    mailbox = {
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
    return rendered, mailbox


def run_cli(
    rendered_path: Path,
    mailbox_path: Path,
    authorization_path: Path,
    *,
    check: bool = False,
    consumption_directory: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    directory = (
        consumption_directory
        if consumption_directory is not None
        else authorization_path.parent / "consumption"
    )
    directory.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(AUTHORIZATION_SCRIPT),
        "--rendered-response",
        str(rendered_path),
        "--mailbox-receipt",
        str(mailbox_path),
        "--consumption-directory",
        str(directory),
        "--authorization-output",
        str(authorization_path),
    ]
    if check:
        command.append("--check")
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def write_inputs(
    tmp_path: Path,
    rendered: dict[str, object],
    mailbox: dict[str, object],
) -> tuple[Path, Path]:
    rendered_path = tmp_path / "rendered.json"
    mailbox_path = tmp_path / "mailbox.json"
    rendered_path.write_text(json.dumps(rendered), encoding="utf-8")
    mailbox_path.write_text(json.dumps(mailbox), encoding="utf-8")
    return rendered_path, mailbox_path


def test_cli_builds_private_packet_without_printing_message_fields(tmp_path):
    rendered, mailbox = ready_inputs()
    rendered_path, mailbox_path = write_inputs(
        tmp_path,
        rendered,
        mailbox,
    )
    authorization_path = tmp_path / "authorization.json"

    result = run_cli(rendered_path, mailbox_path, authorization_path)

    assert result.returncode == 0, result.stderr
    assert authorization_path.is_file()
    summary = json.loads(result.stdout)
    authorization = json.loads(
        authorization_path.read_text(encoding="utf-8")
    )
    phrase = authorization["exact_action_time_approval_phrase"]
    assert summary["status"] == "READY_FOR_SINGLE_USE_EXACT_APPROVAL"
    assert summary["outputs_written"] is True
    assert summary["exact_approval_phrase_printed"] is False
    assert summary["send_authorized"] is False
    assert summary["send_performed"] is False
    assert summary["consumption_directory_sha256"] == authorization[
        "approval_binding"
    ]["consumption_directory_sha256"]
    assert phrase not in result.stdout
    assert "reviewer@example.org" not in result.stdout
    assert "synthetic-message-id" not in result.stdout
    assert rendered["subject"] not in result.stdout
    assert rendered["body"] not in result.stdout
    serialized_authorization = json.dumps(authorization)
    assert "reviewer@example.org" not in serialized_authorization
    assert "synthetic-message-id" not in serialized_authorization
    assert rendered["subject"] not in serialized_authorization
    assert rendered["body"] not in serialized_authorization


def test_cli_check_mode_validates_without_writing(tmp_path):
    rendered, mailbox = ready_inputs()
    rendered_path, mailbox_path = write_inputs(
        tmp_path,
        rendered,
        mailbox,
    )
    authorization_path = tmp_path / "authorization.json"

    result = run_cli(
        rendered_path,
        mailbox_path,
        authorization_path,
        check=True,
    )

    assert result.returncode == 0, result.stderr
    assert authorization_path.exists() is False
    summary = json.loads(result.stdout)
    assert summary["outputs_written"] is False
    assert (
        summary["exact_approval_phrase_stored_in_private_output"] is False
    )


def test_cli_rejects_stale_mailbox_receipt_without_writing(tmp_path):
    rendered, mailbox = ready_inputs()
    stale = datetime.now(timezone.utc) - timedelta(hours=1)
    stale_utc = stale.replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )
    mailbox["checked_utc"] = stale_utc
    mailbox["draft_readback_checked_utc"] = stale_utc
    rendered_path, mailbox_path = write_inputs(
        tmp_path,
        rendered,
        mailbox,
    )
    authorization_path = tmp_path / "authorization.json"

    result = run_cli(rendered_path, mailbox_path, authorization_path)

    assert result.returncode != 0
    assert authorization_path.exists() is False
    assert "ACTION_TIME_MAILBOX_SEARCH_STALE" in result.stderr


def test_cli_rejects_duplicate_json_keys(tmp_path):
    rendered, mailbox = ready_inputs()
    rendered_path, mailbox_path = write_inputs(
        tmp_path,
        rendered,
        mailbox,
    )
    rendered_path.write_text(
        '{"schema":"a","schema":"b"}',
        encoding="utf-8",
    )
    authorization_path = tmp_path / "authorization.json"

    result = run_cli(rendered_path, mailbox_path, authorization_path)

    assert result.returncode != 0
    assert authorization_path.exists() is False
    assert "DUPLICATE_JSON_KEY:schema" in result.stderr
