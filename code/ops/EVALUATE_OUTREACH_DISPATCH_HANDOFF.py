from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import BUILD_OUTREACH_RESPONSE_TEMPLATE_REGISTRY as registry


APPROVAL_PHRASE_ENV = "LUMA_OUTREACH_EXACT_APPROVAL_PHRASE"
HUMAN_UNLOCK_TOKEN_ENV = "LUMA_HUMAN_UNLOCK_TOKEN"
HUMAN_UNLOCK_SHA256_ENV = "LUMA_HUMAN_UNLOCK_SHA256"


def read_authorization(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=registry._reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise registry.OutreachRegistryError(
            "ACTION_TIME_AUTHORIZATION_NOT_OBJECT"
        )
    return payload


def current_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def consumption_receipt_path(
    authorization: dict[str, Any],
    consumption_directory: Path,
) -> Path:
    if (
        not consumption_directory.exists()
        or not consumption_directory.is_dir()
    ):
        raise registry.OutreachRegistryError(
            "CONSUMPTION_DIRECTORY_REQUIRED"
        )
    binding = authorization.get("dispatch_binding")
    if not isinstance(binding, dict):
        raise registry.OutreachRegistryError(
            "DISPATCH_BINDING_MISSING"
        )
    binding_sha256 = registry._normalize_required_sha256(
        binding.get("binding_sha256"),
        "DISPATCH_BINDING_SHA256_INVALID",
    )
    return consumption_directory / f"{binding_sha256}.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one outreach dispatch handoff without sending email. "
            "The exact approval phrase and private HumanUnlock are accepted "
            "only through protected runtime environment variables."
        )
    )
    parser.add_argument(
        "--authorization",
        type=Path,
        required=True,
        help="Path to a private action-time authorization JSON artifact.",
    )
    parser.add_argument(
        "--current-utc",
        help="Aware UTC timestamp; defaults to the current wall clock.",
    )
    parser.add_argument(
        "--consumption-directory",
        type=Path,
        required=True,
        help=(
            "Private canonical directory containing deterministic "
            "dispatch-consumption receipts."
        ),
    )
    parser.add_argument(
        "--dispatch-consumed",
        action="store_true",
        help="Fail closed when the single-use binding was already consumed.",
    )
    args = parser.parse_args()

    authorization = read_authorization(args.authorization)
    consumption_path = consumption_receipt_path(
        authorization,
        args.consumption_directory,
    )
    consumption_receipt_present = consumption_path.exists()
    handoff = registry.evaluate_action_time_dispatch_handoff(
        authorization,
        exact_approval_phrase=os.environ.get(APPROVAL_PHRASE_ENV, ""),
        current_utc=args.current_utc or current_utc(),
        human_unlock_token=os.environ.get(HUMAN_UNLOCK_TOKEN_ENV),
        expected_human_unlock_sha256=os.environ.get(
            HUMAN_UNLOCK_SHA256_ENV
        ),
        dispatch_consumed=(
            args.dispatch_consumed or consumption_receipt_present
        ),
        consumption_directory_checked=True,
        consumption_receipt_present=consumption_receipt_present,
    )
    print(json.dumps(handoff, indent=2, sort_keys=True))
    return 0 if handoff["dispatch_authorized"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
