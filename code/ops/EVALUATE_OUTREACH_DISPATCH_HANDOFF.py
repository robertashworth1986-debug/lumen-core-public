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
        "--dispatch-consumed",
        action="store_true",
        help="Fail closed when the single-use binding was already consumed.",
    )
    args = parser.parse_args()

    handoff = registry.evaluate_action_time_dispatch_handoff(
        read_authorization(args.authorization),
        exact_approval_phrase=os.environ.get(APPROVAL_PHRASE_ENV, ""),
        current_utc=args.current_utc or current_utc(),
        human_unlock_token=os.environ.get(HUMAN_UNLOCK_TOKEN_ENV),
        expected_human_unlock_sha256=os.environ.get(
            HUMAN_UNLOCK_SHA256_ENV
        ),
        dispatch_consumed=args.dispatch_consumed,
    )
    print(json.dumps(handoff, indent=2, sort_keys=True))
    return 0 if handoff["dispatch_authorized"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
