from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import BUILD_OUTREACH_RESPONSE_TEMPLATE_REGISTRY as registry


def read_json_object(path: Path, error_code: str) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=registry._reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise registry.OutreachRegistryError(error_code)
    return payload


def current_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise registry.OutreachRegistryError(
            "DISPATCH_CONSUMPTION_RECEIPT_ALREADY_EXISTS"
        )
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
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise registry.OutreachRegistryError(
                "DISPATCH_CONSUMPTION_RECEIPT_ALREADY_EXISTS"
            ) from exc
        except OSError:
            try:
                exclusive_descriptor = os.open(
                    path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError as exc:
                raise registry.OutreachRegistryError(
                    "DISPATCH_CONSUMPTION_RECEIPT_ALREADY_EXISTS"
                ) from exc
            try:
                with os.fdopen(
                    exclusive_descriptor,
                    "w",
                    encoding="utf-8",
                    newline="\n",
                ) as handle:
                    handle.write(serialized)
                    handle.flush()
                    os.fsync(handle.fileno())
            except BaseException:
                path.unlink(missing_ok=True)
                raise
    finally:
        temporary_path.unlink(missing_ok=True)


def receipt_summary(
    receipt: dict[str, Any],
    output_path: Path,
    *,
    outputs_written: bool,
) -> dict[str, Any]:
    return {
        "schema": (
            "lumencore.outreach_dispatch_consumption_build_receipt.v1"
        ),
        "status": receipt["status"],
        "captured_utc": receipt["captured_utc"],
        "sent_utc": receipt["sent_utc"],
        "dispatch_binding_sha256": receipt[
            "dispatch_binding_sha256"
        ],
        "dispatch_consumption_receipt_sha256": receipt[
            "receipt_sha256"
        ],
        "receipt_output": str(output_path),
        "outputs_written": outputs_written,
        "dispatch_reservation_finalized": outputs_written,
        "single_use_binding_consumed": True,
        "duplicate_send_allowed": False,
        "send_performed_by_receipt_builder": False,
        "receipt_builder_can_send_email": False,
        "private_message_fields_omitted_from_stdout": True,
    }


def deterministic_receipt_path(
    consumption_directory: Path,
    receipt: dict[str, Any],
) -> Path:
    binding_sha256 = registry._normalize_required_sha256(
        receipt.get("dispatch_binding_sha256"),
        "DISPATCH_CONSUMPTION_BINDING_SHA256_INVALID",
    )
    return consumption_directory / f"{binding_sha256}.json"


def deterministic_reservation_path(
    consumption_directory: Path,
    authorization: dict[str, Any],
) -> Path:
    binding = authorization.get("dispatch_binding")
    if not isinstance(binding, dict):
        raise registry.OutreachRegistryError(
            "DISPATCH_RESERVATION_BINDING_MISSING"
        )
    binding_sha256 = registry._normalize_required_sha256(
        binding.get("binding_sha256"),
        "DISPATCH_RESERVATION_BINDING_SHA256_INVALID",
    )
    return consumption_directory / f"{binding_sha256}.pending"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture a privacy-safe single-use dispatch-consumption receipt "
            "from an authorized handoff and fresh private Gmail SENT "
            "observation. This tool cannot send email."
        )
    )
    parser.add_argument(
        "--authorization",
        type=Path,
        required=True,
        help="Private action-time authorization JSON.",
    )
    parser.add_argument(
        "--dispatch-handoff",
        type=Path,
        required=True,
        help="No-send authorized dispatch-handoff receipt JSON.",
    )
    parser.add_argument(
        "--post-send-observation",
        type=Path,
        required=True,
        help="Fresh private Gmail SENT observation JSON.",
    )
    parser.add_argument(
        "--consumption-directory",
        type=Path,
        required=True,
        help=(
            "Private canonical directory for the deterministic, exclusive "
            "consumption receipt."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and summarize without writing a receipt.",
    )
    args = parser.parse_args()

    consumption_directory_sha256 = (
        registry.consumption_directory_identity_sha256(
            args.consumption_directory
        )
    )
    authorization = read_json_object(
        args.authorization,
        "DISPATCH_CONSUMPTION_AUTHORIZATION_NOT_OBJECT",
    )
    approval_binding = authorization.get("approval_binding")
    if not isinstance(approval_binding, dict):
        raise registry.OutreachRegistryError(
            "DISPATCH_CONSUMPTION_APPROVAL_BINDING_MISSING"
        )
    bound_consumption_directory_sha256 = (
        registry._normalize_required_sha256(
            approval_binding.get("consumption_directory_sha256"),
            "DISPATCH_CONSUMPTION_BOUND_DIRECTORY_SHA256_INVALID",
        )
    )
    if (
        consumption_directory_sha256
        != bound_consumption_directory_sha256
    ):
        raise registry.OutreachRegistryError(
            "DISPATCH_CONSUMPTION_DIRECTORY_IDENTITY_MISMATCH"
        )
    handoff = read_json_object(
        args.dispatch_handoff,
        "DISPATCH_CONSUMPTION_HANDOFF_NOT_OBJECT",
    )
    post_send_observation = read_json_object(
        args.post_send_observation,
        "POST_SEND_OBSERVATION_NOT_OBJECT",
    )
    reservation_path = deterministic_reservation_path(
        args.consumption_directory,
        authorization,
    )
    if not reservation_path.is_file():
        raise registry.OutreachRegistryError(
            "DISPATCH_RESERVATION_REQUIRED"
        )
    dispatch_reservation = read_json_object(
        reservation_path,
        "DISPATCH_RESERVATION_NOT_OBJECT",
    )
    receipt = registry.build_dispatch_consumption_receipt(
        authorization,
        handoff,
        post_send_observation,
        dispatch_reservation,
        current_utc=current_utc(),
        consumption_directory_sha256=consumption_directory_sha256,
    )
    receipt_output = deterministic_receipt_path(
        args.consumption_directory,
        receipt,
    )
    if not args.check:
        write_json_exclusive(receipt_output, receipt)
        reservation_path.unlink()
    print(
        json.dumps(
            receipt_summary(
                receipt,
                receipt_output,
                outputs_written=not args.check,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
