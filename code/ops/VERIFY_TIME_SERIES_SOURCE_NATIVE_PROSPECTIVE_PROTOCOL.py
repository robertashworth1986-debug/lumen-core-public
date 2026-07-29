from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_JSON = (
    ROOT
    / "config"
    / "time_series_source_native_prospective_protocol_v1.json"
)
OUT_JSON = (
    ROOT
    / "out"
    / "ops"
    / "time_series_source_native_prospective_protocol_status.json"
)


def now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_protocol(path: Path = PROTOCOL_JSON) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("prospective protocol must be a JSON object")
    return payload


def validate_protocol(
    protocol: dict[str, Any],
    *,
    root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    expected_payload_sha256 = str(
        protocol.get("protocol_payload_sha256", "")
    ).lower()
    unsigned = {
        key: value
        for key, value in protocol.items()
        if key != "protocol_payload_sha256"
    }
    observed_payload_sha256 = canonical_sha256(unsigned)
    if expected_payload_sha256 != observed_payload_sha256:
        errors.append("protocol_payload_sha256_mismatch")
    if (
        protocol.get("schema")
        != "time_series_source_native_prospective_protocol.v1"
    ):
        errors.append("protocol_schema_invalid")
    if protocol.get("status") != "FROZEN_AWAITING_FUTURE_OBSERVATIONS":
        errors.append("protocol_not_frozen_waiting")

    baselines = protocol.get("registered_baselines")
    if not isinstance(baselines, list) or len(baselines) != 8:
        errors.append("registered_baseline_count_not_eight")
    hypothesis = protocol.get("primary_hypothesis_family")
    if (
        not isinstance(hypothesis, dict)
        or hypothesis.get("contrast_count") != 16
        or hypothesis.get("correction") != "one_sided_holm_familywise"
    ):
        errors.append("primary_hypothesis_family_invalid")

    current_state = protocol.get("current_state")
    if (
        not isinstance(current_state, dict)
        or current_state.get("eligible_future_observation_count") != 0
        or current_state.get("promotion_decision")
        != "WAITING_FOR_NEW_SOURCE_ROWS"
        or current_state.get("performance_claim_allowed") is not False
    ):
        errors.append("current_state_not_fail_closed")

    amendments = protocol.get("freeze_amendments", [])
    if not isinstance(amendments, list):
        errors.append("freeze_amendments_invalid")
        amendments = []
    for index, amendment in enumerate(amendments):
        prefix = f"freeze_amendments[{index}]"
        if not isinstance(amendment, dict):
            errors.append(f"{prefix}_invalid")
            continue
        if amendment.get("eligible_future_observation_count_at_amendment") != 0:
            errors.append(f"{prefix}_post_observation_change_forbidden")
        for key in (
            "outcome_dependent_change",
            "candidate_selection_changed",
            "registered_baselines_changed",
            "primary_endpoint_changed",
            "sample_gates_changed",
            "decision_rule_changed",
        ):
            if amendment.get(key) is not False:
                errors.append(f"{prefix}_{key}_must_be_false")
        prior_hash = str(amendment.get("prior_artifact_sha256", "")).lower()
        amended_hash = str(
            amendment.get("amended_artifact_sha256", "")
        ).lower()
        if len(prior_hash) != 64 or len(amended_hash) != 64:
            errors.append(f"{prefix}_artifact_hash_invalid")

    artifacts = protocol.get("frozen_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("frozen_artifact_manifest_missing")
        return errors
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append("frozen_artifact_entry_invalid")
            continue
        relative = str(artifact.get("path", ""))
        expected = str(artifact.get("sha256", "")).lower()
        path = root / relative
        if not relative or not path.is_file():
            errors.append(f"frozen_artifact_missing:{relative}")
            continue
        observed = file_sha256(path)
        if observed != expected:
            errors.append(f"frozen_artifact_hash_mismatch:{relative}")
    return errors


def build_status(
    protocol: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    receipt = {
        "schema": "time_series_source_native_prospective_protocol_status.v1",
        "generated_utc": now_utc(),
        "protocol_id": protocol.get("protocol_id", ""),
        "protocol_payload_sha256": protocol.get(
            "protocol_payload_sha256", ""
        ),
        "protocol_status": protocol.get("status", ""),
        "verification_passed": not errors,
        "verification_errors": errors,
        "frozen_artifact_count": len(
            protocol.get("frozen_artifacts", [])
            if isinstance(protocol.get("frozen_artifacts"), list)
            else []
        ),
        "eligible_future_observation_count": (
            protocol.get("current_state", {}).get(
                "eligible_future_observation_count", 0
            )
            if isinstance(protocol.get("current_state"), dict)
            else 0
        ),
        "promotion_decision": (
            protocol.get("current_state", {}).get(
                "promotion_decision", "INVALID"
            )
            if isinstance(protocol.get("current_state"), dict)
            else "INVALID"
        ),
        "performance_claim_allowed": False,
        "field_validation_claim_allowed": False,
        "real_dollar_claim_allowed": False,
        "live_execution_allowed": False,
        "claim_boundary": protocol.get("claim_boundary", ""),
    }
    receipt["status_receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    protocol = read_protocol()
    errors = validate_protocol(protocol)
    status = build_status(protocol, errors)
    if not args.check:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
