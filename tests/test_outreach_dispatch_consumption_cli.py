from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_OUTREACH_RESPONSE_TEMPLATE_REGISTRY.py"
)
CONSUMPTION_SCRIPT = (
    ROOT / "code" / "ops" / "CAPTURE_OUTREACH_DISPATCH_CONSUMPTION.py"
)
HANDOFF_SCRIPT = (
    ROOT / "code" / "ops" / "EVALUATE_OUTREACH_DISPATCH_HANDOFF.py"
)
SYNTHETIC_UNLOCK = "synthetic-private-unlock"


def load_registry():
    spec = importlib.util.spec_from_file_location(
        "outreach_dispatch_consumption_cli_test",
        REGISTRY_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def ready_inputs(
    *,
    consumption_directory: Path,
    base: datetime | None = None,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    module = load_registry()
    consumption_directory.mkdir(parents=True, exist_ok=True)
    opened = (base or (datetime.now(timezone.utc) - timedelta(seconds=10)))
    opened = opened.replace(microsecond=0)
    rendered = module.render_response(
        "REQUESTED_INFORMATION_REPLY",
        {
            "recipient_name": "Reviewer",
            "recipient_email": "reviewer@example.org",
            "source_message_id": "synthetic-source-message-id",
            "source_subject": "Requested information",
            "sender_name": "Founder",
            "sender_title": "Founder / Systems Architect",
            "organization_name": "LumenCore",
            "requested_information": "One bounded technical-review summary.",
        },
    )
    binding = rendered["dispatch_binding"]
    mailbox = {
        "attachment_count": binding["attachment_count"],
        "attachment_set_sha256": binding["attachment_set_sha256"],
        "bcc_count": 0,
        "body_sha256": binding["body_sha256"],
        "cc_count": 0,
        "checked_utc": iso_z(opened),
        "current_draft_only": True,
        "draft_present": True,
        "draft_readback_checked_utc": iso_z(opened),
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
    authorization = module.build_action_time_authorization(
        rendered,
        mailbox,
        current_utc=iso_z(opened),
        consumption_directory_sha256=(
            module.consumption_directory_identity_sha256(
                consumption_directory
            )
        ),
    )
    unlock = SYNTHETIC_UNLOCK
    handoff_evaluated = opened + timedelta(seconds=1)
    reservation = module.build_dispatch_reservation(
        authorization,
        current_utc=iso_z(handoff_evaluated),
    )
    reservation_path = consumption_directory / (
        f"{binding['binding_sha256']}.pending"
    )
    reservation_path.write_text(
        json.dumps(reservation),
        encoding="utf-8",
    )
    handoff = module.evaluate_action_time_dispatch_handoff(
        authorization,
        exact_approval_phrase=authorization[
            "exact_action_time_approval_phrase"
        ],
        current_utc=iso_z(handoff_evaluated),
        human_unlock_token=unlock,
        expected_human_unlock_sha256=module.sha256_bytes(
            unlock.encode("utf-8")
        ),
        consumption_directory_checked=True,
        consumption_directory_sha256=(
            module.consumption_directory_identity_sha256(
                consumption_directory
            )
        ),
        consumption_receipt_present=False,
        dispatch_reservation_created=True,
        dispatch_reservation_present=False,
        dispatch_reservation_sha256=reservation[
            "reservation_sha256"
        ],
    )
    observation = {
        "attachment_count": binding["attachment_count"],
        "attachment_set_sha256": binding["attachment_set_sha256"],
        "bcc_count": 0,
        "body_sha256": binding["body_sha256"],
        "cc_count": 0,
        "checked_utc": iso_z(datetime.now(timezone.utc)),
        "draft_label_present": False,
        "full_mailbox_search_completed": True,
        "identifiers_private": True,
        "matching_current_draft_count": 0,
        "matching_sent_count": 1,
        "message_body_omitted": True,
        "message_id": "private-message-id-123",
        "recipient_route_sha256": binding["recipient_route_sha256"],
        "schema": "lumencore.outreach_post_send_observation.private.v1",
        "search_scope": "ALL_MAIL_BOUND_ROUTE_THREAD_SUBJECT_BODY",
        "sent_label_present": True,
        "sent_utc": iso_z(opened + timedelta(seconds=2)),
        "source_message_id_sha256": binding["source_message_id_sha256"],
        "subject_sha256": binding["subject_sha256"],
        "thread_id": "private-thread-id-456",
    }
    return authorization, handoff, observation


def write_inputs(
    tmp_path: Path,
    authorization: dict[str, object],
    handoff: dict[str, object],
    observation: dict[str, object],
) -> tuple[Path, Path, Path]:
    authorization_path = tmp_path / "authorization.json"
    handoff_path = tmp_path / "handoff.json"
    observation_path = tmp_path / "observation.json"
    authorization_path.write_text(
        json.dumps(authorization),
        encoding="utf-8",
    )
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
    observation_path.write_text(
        json.dumps(observation),
        encoding="utf-8",
    )
    return authorization_path, handoff_path, observation_path


def run_cli(
    authorization_path: Path,
    handoff_path: Path,
    observation_path: Path,
    consumption_directory: Path,
    *,
    check: bool = False,
    human_unlock_token: str | None = SYNTHETIC_UNLOCK,
    expected_human_unlock_sha256: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(CONSUMPTION_SCRIPT),
        "--authorization",
        str(authorization_path),
        "--dispatch-handoff",
        str(handoff_path),
        "--post-send-observation",
        str(observation_path),
        "--consumption-directory",
        str(consumption_directory),
    ]
    if check:
        command.append("--check")
    env = os.environ.copy()
    if human_unlock_token is None:
        env.pop("LUMA_HUMAN_UNLOCK_TOKEN", None)
    else:
        env["LUMA_HUMAN_UNLOCK_TOKEN"] = human_unlock_token
    if expected_human_unlock_sha256 is None and human_unlock_token is not None:
        expected_human_unlock_sha256 = load_registry().sha256_bytes(
            human_unlock_token.encode("utf-8")
        )
    if expected_human_unlock_sha256 is None:
        env.pop("LUMA_HUMAN_UNLOCK_SHA256", None)
    else:
        env["LUMA_HUMAN_UNLOCK_SHA256"] = (
            expected_human_unlock_sha256
        )
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_captures_redacted_single_use_consumption_receipt(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    paths = write_inputs(tmp_path, authorization, handoff, observation)
    receipt_path = consumption_directory / (
        f"{authorization['dispatch_binding']['binding_sha256']}.json"
    )

    result = run_cli(*paths, consumption_directory)

    assert result.returncode == 0, result.stderr
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    summary = json.loads(result.stdout)
    assert receipt["single_use_binding_consumed"] is True
    assert receipt["duplicate_send_allowed"] is False
    assert receipt["send_performed"] is True
    assert receipt["delivery_confirmed"] is False
    assert receipt["send_performed_by_receipt_builder"] is False
    assert receipt["receipt_builder_can_send_email"] is False
    assert summary["outputs_written"] is True
    assert summary["dispatch_reservation_finalized"] is True
    assert summary["handoff_keyed_authentication_verified"] is True
    assert summary["private_human_unlock_revalidated"] is True
    assert not (
        consumption_directory
        / f"{authorization['dispatch_binding']['binding_sha256']}.pending"
    ).exists()
    serialized = json.dumps(receipt)
    assert observation["message_id"] not in serialized
    assert observation["thread_id"] not in serialized
    assert "reviewer@example.org" not in serialized
    assert authorization["dispatch_binding"]["body_sha256"] not in result.stdout
    assert SYNTHETIC_UNLOCK not in result.stdout
    assert SYNTHETIC_UNLOCK not in serialized

    module = load_registry()
    unlock = "synthetic-private-unlock"
    env = os.environ.copy()
    env["LUMA_OUTREACH_EXACT_APPROVAL_PHRASE"] = authorization[
        "exact_action_time_approval_phrase"
    ]
    env["LUMA_HUMAN_UNLOCK_TOKEN"] = unlock
    env["LUMA_HUMAN_UNLOCK_SHA256"] = module.sha256_bytes(
        unlock.encode("utf-8")
    )
    replay = subprocess.run(
        [
            sys.executable,
            str(HANDOFF_SCRIPT),
            "--authorization",
            str(paths[0]),
            "--consumption-directory",
            str(consumption_directory),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert replay.returncode == 3, replay.stderr
    replay_receipt = json.loads(replay.stdout)
    assert replay_receipt["consumption_receipt_present"] is True
    assert replay_receipt["single_use_binding_consumed"] is True
    assert replay_receipt["dispatch_authorized"] is False
    assert "SINGLE_USE_BINDING_ALREADY_CONSUMED" in replay_receipt[
        "blockers"
    ]


def test_cli_check_mode_validates_without_writing(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    paths = write_inputs(tmp_path, authorization, handoff, observation)
    receipt_path = consumption_directory / (
        f"{authorization['dispatch_binding']['binding_sha256']}.json"
    )

    result = run_cli(*paths, consumption_directory, check=True)

    assert result.returncode == 0, result.stderr
    assert receipt_path.exists() is False
    assert json.loads(result.stdout)["outputs_written"] is False
    assert (
        consumption_directory
        / f"{authorization['dispatch_binding']['binding_sha256']}.pending"
    ).is_file()


def test_cli_rejects_unbound_consumption_directory(tmp_path):
    canonical_directory = tmp_path / "canonical-consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=canonical_directory
    )
    paths = write_inputs(tmp_path, authorization, handoff, observation)
    alternate_directory = tmp_path / "alternate-consumption"
    alternate_directory.mkdir()

    result = run_cli(*paths, alternate_directory)

    assert result.returncode != 0
    assert "DISPATCH_CONSUMPTION_DIRECTORY_IDENTITY_MISMATCH" in result.stderr
    assert not list(alternate_directory.glob("*.json"))


def test_cli_requires_exact_pending_dispatch_reservation(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    paths = write_inputs(tmp_path, authorization, handoff, observation)
    reservation_path = consumption_directory / (
        f"{authorization['dispatch_binding']['binding_sha256']}.pending"
    )
    reservation_path.unlink()

    result = run_cli(*paths, consumption_directory)

    assert result.returncode != 0
    assert "DISPATCH_RESERVATION_REQUIRED" in result.stderr
    assert not list(consumption_directory.glob("*.json"))


def test_cli_requires_private_unlock_again_for_consumption(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    paths = write_inputs(tmp_path, authorization, handoff, observation)

    result = run_cli(
        *paths,
        consumption_directory,
        human_unlock_token=None,
    )

    assert result.returncode != 0
    assert (
        "DISPATCH_CONSUMPTION_HUMAN_UNLOCK_TOKEN_REQUIRED"
        in result.stderr
    )
    assert not list(consumption_directory.glob("*.json"))


def test_cli_rejects_wrong_private_unlock_for_consumption(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    paths = write_inputs(tmp_path, authorization, handoff, observation)
    module = load_registry()

    result = run_cli(
        *paths,
        consumption_directory,
        human_unlock_token="wrong-private-unlock",
        expected_human_unlock_sha256=module.sha256_bytes(
            SYNTHETIC_UNLOCK.encode("utf-8")
        ),
    )

    assert result.returncode != 0
    assert "DISPATCH_CONSUMPTION_HUMAN_UNLOCK_MISMATCH" in result.stderr
    assert not list(consumption_directory.glob("*.json"))


def test_cli_rejects_rehashed_but_unauthenticated_handoff_forgery(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, valid_handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    module = load_registry()
    reservation_path = consumption_directory / (
        f"{authorization['dispatch_binding']['binding_sha256']}.pending"
    )
    reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
    blocked = module.evaluate_action_time_dispatch_handoff(
        authorization,
        exact_approval_phrase=authorization[
            "exact_action_time_approval_phrase"
        ],
        current_utc=valid_handoff["evaluated_utc"],
        human_unlock_token=None,
        expected_human_unlock_sha256=None,
        consumption_directory_checked=True,
        consumption_directory_sha256=(
            module.consumption_directory_identity_sha256(
                consumption_directory
            )
        ),
        consumption_receipt_present=False,
        dispatch_reservation_created=True,
        dispatch_reservation_present=False,
        dispatch_reservation_sha256=reservation["reservation_sha256"],
    )
    forged = dict(blocked)
    forged.update(
        {
            "status": "READY_FOR_CONNECTED_SENDER_SINGLE_USE_DISPATCH",
            "private_human_unlock_configured": True,
            "private_human_unlock_supplied": True,
            "private_human_unlock_valid": True,
            "blockers": [],
            "dispatch_authorized": True,
            "send_authorized": True,
            "handoff_authentication_hmac_sha256": "A" * 64,
        }
    )
    forged["receipt_sha256"] = module.canonical_object_sha256(
        forged,
        omit={"receipt_sha256"},
    )
    paths = write_inputs(tmp_path, authorization, forged, observation)

    result = run_cli(*paths, consumption_directory)

    assert result.returncode != 0
    assert "DISPATCH_HANDOFF_AUTHENTICATION_HMAC_MISMATCH" in result.stderr
    assert not list(consumption_directory.glob("*.json"))


def test_cli_rejects_duplicate_sent_copy_count(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    observation["matching_sent_count"] = 2
    paths = write_inputs(tmp_path, authorization, handoff, observation)

    result = run_cli(*paths, consumption_directory)

    assert result.returncode != 0
    assert "POST_SEND_COUNT_INVALID:matching_sent_count" in result.stderr


def test_cli_rejects_surviving_draft(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    observation["draft_label_present"] = True
    observation["matching_current_draft_count"] = 1
    paths = write_inputs(tmp_path, authorization, handoff, observation)

    result = run_cli(*paths, consumption_directory)

    assert result.returncode != 0
    assert "POST_SEND_DRAFT_LABEL_PRESENT" in result.stderr


def test_cli_rejects_hash_drift(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    observation["body_sha256"] = "A" * 64
    paths = write_inputs(tmp_path, authorization, handoff, observation)

    result = run_cli(*paths, consumption_directory)

    assert result.returncode != 0
    assert "POST_SEND_BODY_MISMATCH" in result.stderr


def test_cli_rejects_stale_post_send_search(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    observation["checked_utc"] = iso_z(
        datetime.now(timezone.utc) - timedelta(hours=1)
    )
    paths = write_inputs(tmp_path, authorization, handoff, observation)

    result = run_cli(*paths, consumption_directory)

    assert result.returncode != 0
    assert "POST_SEND_MAILBOX_SEARCH_STALE" in result.stderr


def test_cli_rejects_send_at_approval_expiry(tmp_path):
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory,
        base=base,
    )
    observation["sent_utc"] = authorization["approval_binding"][
        "approval_window_expires_utc"
    ]
    paths = write_inputs(tmp_path, authorization, handoff, observation)

    result = run_cli(*paths, consumption_directory)

    assert result.returncode != 0
    assert "POST_SEND_AT_OR_AFTER_APPROVAL_EXPIRY" in result.stderr


def test_cli_refuses_to_overwrite_existing_consumption_receipt(tmp_path):
    consumption_directory = tmp_path / "consumption"
    authorization, handoff, observation = ready_inputs(
        consumption_directory=consumption_directory
    )
    paths = write_inputs(tmp_path, authorization, handoff, observation)
    receipt_path = consumption_directory / (
        f"{authorization['dispatch_binding']['binding_sha256']}.json"
    )
    receipt_path.write_text("existing\n", encoding="utf-8")

    result = run_cli(*paths, consumption_directory)

    assert result.returncode != 0
    assert "DISPATCH_CONSUMPTION_RECEIPT_ALREADY_EXISTS" in result.stderr
    assert receipt_path.read_text(encoding="utf-8") == "existing\n"
