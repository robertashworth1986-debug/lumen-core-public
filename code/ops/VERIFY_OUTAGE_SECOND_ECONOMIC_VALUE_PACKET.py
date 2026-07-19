#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


OPS_DIR = Path(__file__).resolve().parent
if str(OPS_DIR) not in sys.path:
    sys.path.insert(0, str(OPS_DIR))

import BUILD_OUTAGE_SECOND_ECONOMIC_VALUE_PACKET as core  # noqa: E402


EconomicProtocolError = core.EconomicProtocolError
DEFAULT_BUNDLE_DIR = core.DEFAULT_OUTPUT_DIR
file_sha256 = core.file_sha256
bytes_sha256 = core.bytes_sha256
strict_json_loads = core.strict_json_loads
canonical_json_bytes = core.canonical_json_bytes
stable_sha256 = core.stable_sha256
receipt_signing_bytes = core.receipt_signing_bytes
receipt_signing_payload_sha256 = core.receipt_signing_payload_sha256


def verify_packet(
    bundle_dir: Path,
    *,
    artifact_root: Path | None = None,
    receipt_artifacts: Mapping[str, Mapping[str, Path]] | None = None,
    trusted_key_sha256_by_role: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    return core.verify_bundle(
        bundle_dir,
        artifact_root=artifact_root,
        receipt_artifacts=receipt_artifacts,
        trusted_key_sha256_by_role=trusted_key_sha256_by_role,
        now=now,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline fail-closed verifier for an outage-second economic bundle. "
            "It recomputes the exact private artifact, source hashes, receipt bindings, "
            "Ed25519 signatures, redacted public files, and publication manifest."
        )
    )
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE_DIR)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument(
        "--now-utc",
        help="Optional UTC verification time for deterministic synthetic testing.",
    )
    core.add_receipt_cli_arguments(parser)
    args = parser.parse_args()
    try:
        now = (
            core.parse_utc_timestamp(args.now_utc, "--now-utc")
            if args.now_utc is not None
            else None
        )
        report = verify_packet(
            args.bundle,
            artifact_root=args.artifact_root,
            receipt_artifacts=core._receipt_cli_artifacts(args),
            trusted_key_sha256_by_role=core._trusted_cli_hashes(args),
            now=now,
        )
    except (EconomicProtocolError, FileNotFoundError, FileExistsError, OSError) as exc:
        print(
            json.dumps(
                {
                    "schema": "outage_second_economic_bundle_verification.v1",
                    "status": "FAIL_CLOSED",
                    "error": str(exc),
                    "accepted_estimated_avoided_cost_claim_allowed": False,
                    "public_economic_release_allowed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
