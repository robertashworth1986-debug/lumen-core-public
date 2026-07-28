from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import BUILD_OUTREACH_RESPONSE_TEMPLATE_REGISTRY as registry


def read_private_json(path: Path, error_code: str) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=registry._reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise registry.OutreachRegistryError(error_code)
    return payload


def current_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_private_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def authorization_summary(
    authorization: dict[str, Any],
    output_path: Path,
    *,
    outputs_written: bool,
) -> dict[str, Any]:
    approval_binding = authorization["approval_binding"]
    dispatch_binding = authorization["dispatch_binding"]
    return {
        "schema": "lumencore.outreach_action_time_authorization_build_receipt.v1",
        "status": authorization["status"],
        "generated_utc": authorization["generated_utc"],
        "approval_window_expires_utc": approval_binding[
            "approval_window_expires_utc"
        ],
        "approval_binding_sha256": approval_binding["binding_sha256"],
        "dispatch_binding_sha256": dispatch_binding["binding_sha256"],
        "mailbox_receipt_sha256": authorization["mailbox_receipt_sha256"],
        "authorization_output": str(output_path),
        "outputs_written": outputs_written,
        "exact_approval_phrase_stored_in_private_output": outputs_written,
        "exact_approval_phrase_printed": False,
        "send_authorized": False,
        "send_performed": False,
        "builder_can_send_email": False,
        "private_message_fields_omitted_from_stdout": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build one five-minute outreach authorization packet from a "
            "bound rendered response and fresh mailbox receipt. This tool "
            "writes a private packet but cannot approve or send email."
        )
    )
    parser.add_argument(
        "--rendered-response",
        type=Path,
        required=True,
        help="Path to a private rendered-response JSON artifact.",
    )
    parser.add_argument(
        "--mailbox-receipt",
        type=Path,
        required=True,
        help="Path to a fresh private mailbox-recheck JSON artifact.",
    )
    parser.add_argument(
        "--authorization-output",
        type=Path,
        required=True,
        help="Private output path for the action-time authorization JSON.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and summarize without writing the authorization.",
    )
    args = parser.parse_args()

    authorization = registry.build_action_time_authorization(
        read_private_json(
            args.rendered_response,
            "RENDERED_RESPONSE_NOT_OBJECT",
        ),
        read_private_json(
            args.mailbox_receipt,
            "ACTION_TIME_MAILBOX_RECEIPT_NOT_OBJECT",
        ),
        current_utc=current_utc(),
    )
    if not args.check:
        write_private_json_atomic(args.authorization_output, authorization)
    summary = authorization_summary(
        authorization,
        args.authorization_output,
        outputs_written=not args.check,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
