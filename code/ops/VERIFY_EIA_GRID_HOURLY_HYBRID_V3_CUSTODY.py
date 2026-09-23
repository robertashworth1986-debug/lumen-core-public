#!/usr/bin/env python3
"""Verify a public-safe V3 custody projection without evaluating performance.

The verifier is deterministic for a fixed input directory, policy, frozen source
tree, and ``--as-of-utc`` value.  It performs no network access and never writes
to the frozen protocol, runtime, prediction, settlement, status, or receipt
inputs.  Optional JSON and Markdown outputs contain custody and operational
state only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = (
    ROOT / "config" / "eia_grid_hourly_hybrid_confirmation_custody_watchdog_v1.json"
)
ZERO_HASH = "0" * 64
EXPECTED_POLICY_CANONICAL_SHA256 = (
    "3f0a1f5a3818cfa34c93be2262ca3445a58c27cc05e1f8479e3e4c2304c4a2f2"
)
RECEIPT_SCHEMA = "eia_grid_hourly_hybrid_confirmation_custody_watchdog_receipt.v1"
PERIOD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")

IDENTITY_FIELDS = {
    "protocol_id",
    "protocol_sha256",
    "runtime_sha256",
    "frozen_source_commit",
    "parent_v2_protocol_id",
    "parent_v2_protocol_sha256",
    "parent_v2_protocol_commit",
}
PREDICTION_FIELDS = {
    "schema",
    *IDENTITY_FIELDS,
    "target_period_end_utc",
    "target_interval_start_utc",
    "sealed_utc",
    "seal_lead_seconds",
    "authority_count",
    "authorities",
    "authority_rows",
    "target_actual_present_at_seal",
    "backfilled",
    "scores_suppressed",
    "automatic_promotion_allowed",
    "parent_v2_prediction_panel_record_sha256",
    "parent_v2_prediction_chain_terminal_observed",
    "prior_record_chain_sha256",
    "record_sha256",
}
SETTLEMENT_FIELDS = {
    "schema",
    *IDENTITY_FIELDS,
    "target_period_end_utc",
    "settled_utc",
    "authority_count",
    "authorities",
    "authority_rows",
    "scores_suppressed",
    "automatic_promotion_allowed",
    "v3_prediction_panel_record_sha256",
    "parent_v2_prediction_panel_record_sha256",
    "parent_v2_settlement_panel_record_sha256",
    "parent_v2_settlement_chain_terminal_observed",
    "prior_record_chain_sha256",
    "record_sha256",
}
STATUS_FIELDS = {
    "schema",
    *IDENTITY_FIELDS,
    "generated_utc",
    "prediction_panel_count",
    "settlement_panel_count",
    "complete_utc_day_count",
    "unsettled_panel_count",
    "prediction_terminal_sha256",
    "settlement_terminal_sha256",
    "sample_readiness",
    "scores_suppressed",
    "performance_evaluated",
    "automatic_promotion_allowed",
}
OPERATIONAL_RECEIPT_FIELDS = {
    "schema",
    *IDENTITY_FIELDS,
    "run_utc",
    "prediction_panel_count",
    "settlement_panel_count",
    "complete_utc_day_count",
    "unsettled_panel_count",
    "prediction_terminal_sha256",
    "settlement_terminal_sha256",
    "complete_utc_day_count",
    "unsettled_panel_count",
    "status_sha256",
    "scores_suppressed",
    "performance_evaluated",
    "automatic_promotion_allowed",
}
MANIFEST_FIELDS = {
    "schema",
    "snapshot_kind",
    "generated_utc",
    "frozen_source",
    "files",
    "prediction_panel_count",
    "settlement_panel_count",
    "complete_utc_day_count",
    "unsettled_panel_count",
    "prediction_terminal_sha256",
    "settlement_terminal_sha256",
    "status_sha256",
    "scores_suppressed",
    "performance_evaluated",
    "automatic_promotion_allowed",
}
SAMPLE_READINESS_FIELDS = {
    "operational_shakeout_168_hours",
    "preliminary_720_hours",
    "confirmatory_2160_hours",
    "minimum_90_complete_utc_days",
    "confirmatory_sample_ready",
}
AUTHORITY_ROW_FIELDS = {"respondent", "target_actual_present_at_seal"}
SETTLEMENT_AUTHORITY_ROW_FIELDS = {"respondent"}
FILE_DESCRIPTOR_FIELDS = {"bytes", "sha256"}
SAFE_SUPPRESSION_KEYS = {
    "scores_suppressed",
    "target_actual_present_at_seal",
}
SCORE_BEARING_KEY_MARKERS = (
    "actual_mwh",
    "forecast_mwh",
    "prediction_mwh",
    "absolute_error",
    "scaled_error",
    "comparator",
    "metric",
    "loss",
    "score",
    "improvement",
    "win_rate",
    "weight",
)


class CustodyError(ValueError):
    """A public-safe, reason-coded fail-closed verification error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise CustodyError("DUPLICATE_JSON_KEY", "duplicate JSON keys are forbidden")
        output[key] = value
    return output


def _reject_non_finite(value: str) -> None:
    raise CustodyError("NON_FINITE_NUMBER", "non-finite JSON numbers are forbidden")


def _canonical_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise CustodyError("NON_CANONICAL_JSON", "input is not canonicalizable JSON") from exc
    return rendered.encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_source_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # nosec: Git object identity


def _parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except UnicodeDecodeError as exc:
        raise CustodyError("INVALID_UTF8", f"{label} must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise CustodyError("INVALID_JSON", f"{label} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise CustodyError("INVALID_JSON_SHAPE", f"{label} must be a JSON object")
    return value


def _read_json(path: Path, label: str, maximum_bytes: int) -> dict[str, Any]:
    _require_regular_file(path, label, maximum_bytes)
    return _parse_json_bytes(path.read_bytes(), label)


def _read_jsonl(
    path: Path, label: str, maximum_bytes: int, maximum_records: int
) -> list[dict[str, Any]]:
    _require_regular_file(path, label, maximum_bytes)
    records: list[dict[str, Any]] = []
    with path.open("rb") as handle:
        for raw in handle:
            if not raw.strip():
                raise CustodyError("BLANK_CHAIN_LINE", f"{label} contains a blank line")
            records.append(_parse_json_bytes(raw, label))
            if len(records) > maximum_records:
                raise CustodyError(
                    "CHAIN_RECORD_LIMIT_EXCEEDED", f"{label} exceeds its record limit"
                )
    return records


def _require_regular_file(path: Path, label: str, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise CustodyError("UNSAFE_INPUT_PATH", f"{label} must be a regular file")
    if path.stat().st_size > maximum_bytes:
        raise CustodyError("INPUT_TOO_LARGE", f"{label} exceeds its byte limit")


def _require_fields(value: dict[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise CustodyError(code, "public-safe custody schema fields do not match")


def _require_bool(value: Any, expected: bool, code: str, message: str) -> None:
    if value is not expected:
        raise CustodyError(code, message)


def _require_int(value: Any, code: str, message: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CustodyError(code, message)
    return value


def _require_sha256(value: Any, code: str = "INVALID_SHA256") -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise CustodyError(code, "a lowercase SHA-256 value is required")
    return value


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CustodyError("INVALID_TIMESTAMP", f"{label} must be a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CustodyError("INVALID_TIMESTAMP", f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise CustodyError("INVALID_TIMESTAMP", f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _parse_period(value: Any) -> datetime:
    if not isinstance(value, str) or PERIOD_RE.fullmatch(value) is None:
        raise CustodyError(
            "INVALID_TARGET_PERIOD", "target periods must use YYYY-MM-DDTHH UTC"
        )
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise CustodyError("INVALID_TARGET_PERIOD", "target period is not valid UTC") from exc


def _find_score_leak(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.casefold()
            if key not in SAFE_SUPPRESSION_KEYS and any(
                marker in lowered for marker in SCORE_BEARING_KEY_MARKERS
            ):
                raise CustodyError(
                    "SCORE_LEAKAGE_DETECTED",
                    "a score-bearing or model-comparison field is present",
                )
            _find_score_leak(child)
    elif isinstance(value, list):
        for child in value:
            _find_score_leak(child)


def _load_policy(path: Path) -> tuple[dict[str, Any], str]:
    policy = _read_json(path, "watchdog policy", 1_000_000)
    observed = canonical_sha256(policy)
    if observed != EXPECTED_POLICY_CANONICAL_SHA256:
        raise CustodyError(
            "POLICY_DRIFT_OR_WEAKENING",
            "the immutable watchdog policy changed or was weakened",
        )
    return policy, _file_sha256(path)


def _resolve_beneath(root: Path, relative: str, label: str) -> Path:
    if "\\" in relative:
        raise CustodyError("UNSAFE_INPUT_PATH", f"{label} must use POSIX separators")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or relative.startswith("./"):
        raise CustodyError("UNSAFE_INPUT_PATH", f"{label} is not repository-relative")
    candidate = (root / Path(*pure.parts)).resolve(strict=True)
    try:
        candidate.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise CustodyError("UNSAFE_INPUT_PATH", f"{label} escapes its root") from exc
    return candidate


def _git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip().lower()
    return value if result.returncode == 0 and SHA1_RE.fullmatch(value) else None


def _verify_frozen_source(source_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    source_root = source_root.resolve(strict=True)
    frozen = policy["frozen_source"]
    head = _git_head(source_root)
    if head is not None and head != frozen["commit"]:
        raise CustodyError(
            "FROZEN_SOURCE_COMMIT_MISMATCH",
            "the frozen source checkout is not at the declared commit",
        )
    observed: dict[str, str] = {}
    for name, artifact in frozen["artifacts"].items():
        path = _resolve_beneath(source_root, artifact["path"], f"frozen {name}")
        _require_regular_file(path, f"frozen {name}", 25_000_000)
        raw = _normalized_source_bytes(path)
        sha256 = hashlib.sha256(raw).hexdigest()
        git_blob = _git_blob_sha1(raw)
        if sha256 != artifact["sha256"] or git_blob != artifact["git_blob_sha1"]:
            raise CustodyError(
                "FROZEN_SOURCE_IDENTITY_MISMATCH",
                "a frozen source artifact does not match its immutable identity",
            )
        observed[name] = sha256

    protocol_artifact = frozen["artifacts"]["protocol"]
    protocol_path = _resolve_beneath(
        source_root, protocol_artifact["path"], "frozen protocol"
    )
    protocol = _parse_json_bytes(_normalized_source_bytes(protocol_path), "frozen protocol")
    contract = policy["protocol_contract"]
    window = protocol.get("prospective_window")
    parent = protocol.get("parent_v2")
    inference = protocol.get("inference")
    gates = protocol.get("promotion_gates")
    if not all(isinstance(value, dict) for value in (window, parent, inference, gates)):
        raise CustodyError(
            "FROZEN_PROTOCOL_CONTRACT_MISMATCH",
            "the frozen protocol custody contract is incomplete",
        )
    exact_checks = (
        protocol.get("schema") == "eia_grid_hourly_hybrid_confirmation_protocol.v3",
        protocol.get("protocol_id") == contract["protocol_id"],
        parent.get("protocol_id") == contract["parent_v2_protocol_id"],
        parent.get("protocol_sha256")
        == frozen["artifacts"]["parent_v2_protocol"]["sha256"],
        parent.get("protocol_commit") == contract["parent_v2_protocol_commit"],
        window.get("first_allowed_period_end_utc")
        == contract["first_allowed_period_end_utc"],
        window.get("minimum_seal_lead_seconds")
        == contract["minimum_seal_lead_seconds"],
        window.get("maximum_seal_lead_seconds")
        == contract["maximum_seal_lead_seconds"],
        window.get("operational_shakeout_common_hours")
        == contract["operational_shakeout_common_hours"],
        window.get("preliminary_common_hours")
        == contract["preliminary_common_hours"],
        window.get("confirmatory_common_hours")
        == contract["confirmatory_common_hours"],
        window.get("minimum_complete_utc_days")
        == contract["minimum_complete_utc_days"],
        window.get("backfilled_predictions_allowed") is False,
        protocol.get("balancing_authorities") == contract["balancing_authorities"],
        inference.get("scores_suppressed_before_confirmatory_window_close") is True,
        gates.get("confirmatory", {}).get("automatic_promotion_allowed") is False,
        protocol.get("automatic_promotion_allowed") is False,
    )
    if not all(exact_checks):
        raise CustodyError(
            "FROZEN_PROTOCOL_CONTRACT_MISMATCH",
            "the frozen protocol no longer matches the immutable custody contract",
        )

    runtime_path = _resolve_beneath(
        source_root, frozen["artifacts"]["runtime"]["path"], "frozen runtime"
    )
    runtime_text = _normalized_source_bytes(runtime_path).decode("utf-8")
    runtime_schema_markers = (
        "eia_grid_hourly_hybrid_confirmation_prediction_panel.v3",
        "eia_grid_hourly_hybrid_confirmation_settlement_panel.v3",
        "eia_grid_hourly_hybrid_confirmation_status.v3",
        "eia_grid_hourly_hybrid_confirmation_operational_run.v3",
        "target_actual_present_at_seal",
        "backfilled",
        "automatic_promotion_allowed",
    )
    if any(marker not in runtime_text for marker in runtime_schema_markers):
        raise CustodyError(
            "FROZEN_RUNTIME_SCHEMA_MISMATCH",
            "the frozen runtime is missing a required custody schema marker",
        )
    return {
        "bytes_verified": True,
        "commit_verified": head == frozen["commit"],
        "artifact_count": len(observed),
    }


def _expected_identity(policy: dict[str, Any]) -> dict[str, str]:
    frozen = policy["frozen_source"]
    contract = policy["protocol_contract"]
    return {
        "protocol_id": contract["protocol_id"],
        "protocol_sha256": frozen["artifacts"]["protocol"]["sha256"],
        "runtime_sha256": frozen["artifacts"]["runtime"]["sha256"],
        "frozen_source_commit": frozen["commit"],
        "parent_v2_protocol_id": contract["parent_v2_protocol_id"],
        "parent_v2_protocol_sha256": frozen["artifacts"]["parent_v2_protocol"][
            "sha256"
        ],
        "parent_v2_protocol_commit": contract["parent_v2_protocol_commit"],
    }


def _verify_identity(value: dict[str, Any], policy: dict[str, Any]) -> None:
    expected = _expected_identity(policy)
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise CustodyError(
            "SNAPSHOT_SOURCE_IDENTITY_MISMATCH",
            "a custody record is not bound to the frozen V3 source",
        )


def _verify_boundary_flags(value: dict[str, Any]) -> None:
    _require_bool(
        value.get("scores_suppressed"),
        True,
        "SCORE_SUPPRESSION_DISABLED",
        "score suppression must remain enabled",
    )
    if "performance_evaluated" in value:
        _require_bool(
            value.get("performance_evaluated"),
            False,
            "PERFORMANCE_EVALUATION_EXPOSED",
            "the custody snapshot cannot evaluate performance",
        )
    _require_bool(
        value.get("automatic_promotion_allowed"),
        False,
        "AUTOMATIC_PROMOTION_ENABLED",
        "automatic promotion must remain disabled",
    )


def _verify_authorities(
    value: dict[str, Any], expected: list[str], settlement: bool = False
) -> None:
    if value.get("authority_count") != 8 or value.get("authorities") != expected:
        raise CustodyError(
            "MISSING_OR_CHANGED_AUTHORITY",
            "every complete panel must declare exactly the eight frozen authorities",
        )
    rows = value.get("authority_rows")
    expected_fields = (
        SETTLEMENT_AUTHORITY_ROW_FIELDS if settlement else AUTHORITY_ROW_FIELDS
    )
    if not isinstance(rows, list) or len(rows) != 8:
        raise CustodyError(
            "MISSING_OR_CHANGED_AUTHORITY",
            "every complete panel must contain eight authority custody rows",
        )
    respondents: list[Any] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise CustodyError(
                "MISSING_OR_CHANGED_AUTHORITY",
                "authority custody row fields do not match",
            )
        respondents.append(row.get("respondent"))
        if not settlement and row.get("target_actual_present_at_seal") is not False:
            raise CustodyError(
                "ACTUAL_PRESENT_AT_SEAL",
                "a target actual was present in an authority row at seal time",
            )
    if respondents != expected:
        raise CustodyError(
            "MISSING_OR_CHANGED_AUTHORITY",
            "authority custody rows are incomplete, duplicated, or reordered",
        )


def _verify_chain(
    records: list[dict[str, Any]],
    fields: set[str],
    schema: str,
    policy: dict[str, Any],
    kind: str,
) -> str:
    previous = ZERO_HASH
    seen_targets: set[str] = set()
    expected_authorities = policy["protocol_contract"]["balancing_authorities"]
    first_allowed = _parse_period(
        policy["protocol_contract"]["first_allowed_period_end_utc"]
    )
    for record in records:
        _find_score_leak(record)
        _require_fields(record, fields, f"{kind.upper()}_SCHEMA_MISMATCH")
        if record.get("schema") != schema:
            raise CustodyError(
                f"{kind.upper()}_SCHEMA_MISMATCH",
                f"{kind} custody schema is not allowlisted",
            )
        _verify_identity(record, policy)
        _verify_boundary_flags(record)
        _verify_authorities(record, expected_authorities, settlement=kind == "settlement")
        target_raw = record.get("target_period_end_utc")
        target = _parse_period(target_raw)
        if target < first_allowed:
            raise CustodyError(
                "TARGET_BEFORE_FIRST_ALLOWED_PERIOD",
                "a custody record predates the frozen V3 target window",
            )
        if target_raw in seen_targets:
            raise CustodyError(
                f"DUPLICATE_{kind.upper()}_TARGET",
                f"more than one {kind} panel exists for a target period",
            )
        seen_targets.add(target_raw)
        if record.get("prior_record_chain_sha256") != previous:
            raise CustodyError(
                f"BROKEN_{kind.upper()}_CHAIN",
                f"the {kind} prior-record chain is not continuous",
            )
        observed_hash = _require_sha256(
            record.get("record_sha256"), f"INVALID_{kind.upper()}_RECORD_HASH"
        )
        unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
        if observed_hash != canonical_sha256(unsigned):
            raise CustodyError(
                f"INVALID_{kind.upper()}_RECORD_HASH",
                f"a {kind} record self-hash does not match",
            )

        if kind == "prediction":
            _require_bool(
                record.get("target_actual_present_at_seal"),
                False,
                "ACTUAL_PRESENT_AT_SEAL",
                "a target actual was present when a prediction panel was sealed",
            )
            _require_bool(
                record.get("backfilled"),
                False,
                "BACKFILL_DETECTED",
                "a prediction custody record is marked as backfilled",
            )
            target_start = target - timedelta(hours=1)
            declared_start = _parse_utc(
                record.get("target_interval_start_utc"), "target interval start"
            )
            sealed = _parse_utc(record.get("sealed_utc"), "sealed time")
            lead = record.get("seal_lead_seconds")
            if (
                isinstance(lead, bool)
                or not isinstance(lead, (int, float))
                or not math.isfinite(float(lead))
            ):
                raise CustodyError(
                    "INVALID_SEAL_LEAD", "seal lead must be a finite number of seconds"
                )
            observed_lead = (target_start - sealed).total_seconds()
            contract = policy["protocol_contract"]
            if (
                declared_start != target_start
                or not math.isclose(float(lead), observed_lead, abs_tol=1e-9)
                or observed_lead < contract["minimum_seal_lead_seconds"]
                or observed_lead > contract["maximum_seal_lead_seconds"]
            ):
                raise CustodyError(
                    "INVALID_SEAL_LEAD",
                    "seal lead is outside the frozen 3600-7200 second window",
                )
            _require_sha256(record.get("parent_v2_prediction_panel_record_sha256"))
            _require_sha256(record.get("parent_v2_prediction_chain_terminal_observed"))
        else:
            settled = _parse_utc(record.get("settled_utc"), "settled time")
            if settled < target:
                raise CustodyError(
                    "SETTLED_BEFORE_TARGET_END",
                    "a settlement custody record predates its target end",
                )
            for key in (
                "v3_prediction_panel_record_sha256",
                "parent_v2_prediction_panel_record_sha256",
                "parent_v2_settlement_panel_record_sha256",
                "parent_v2_settlement_chain_terminal_observed",
            ):
                _require_sha256(record.get(key))
        previous = observed_hash
    return previous


def _complete_utc_days(targets: set[str]) -> int:
    by_day: dict[str, set[int]] = {}
    for target in targets:
        by_day.setdefault(target[:10], set()).add(int(target[-2:]))
    required = set(range(24))
    return sum(1 for hours in by_day.values() if hours == required)


def _missing_prediction_period_count(targets: set[str], first_allowed: datetime) -> int:
    if not targets:
        return 0
    latest = max(_parse_period(value) for value in targets)
    expected_count = int((latest - first_allowed).total_seconds() // 3600) + 1
    return max(0, expected_count - len(targets))


def _missing_settlement_period_count(
    prediction_targets: set[str], settlement_targets: set[str]
) -> int:
    if not settlement_targets:
        return 0
    latest_settlement = max(_parse_period(value) for value in settlement_targets)
    expected = {
        value
        for value in prediction_targets
        if _parse_period(value) <= latest_settlement
    }
    return len(expected - settlement_targets)


def _sample_readiness(
    settlement_count: int, complete_day_count: int, policy: dict[str, Any]
) -> dict[str, bool]:
    contract = policy["protocol_contract"]
    hour_168 = settlement_count >= contract["operational_shakeout_common_hours"]
    hour_720 = settlement_count >= contract["preliminary_common_hours"]
    hour_2160 = settlement_count >= contract["confirmatory_common_hours"]
    day_90 = complete_day_count >= contract["minimum_complete_utc_days"]
    return {
        "operational_shakeout_168_hours": hour_168,
        "preliminary_720_hours": hour_720,
        "confirmatory_2160_hours": hour_2160,
        "minimum_90_complete_utc_days": day_90,
        "confirmatory_sample_ready": hour_2160 and day_90,
    }


def _add_reason(
    reasons: list[dict[str, str]], code: str, severity: str, message: str
) -> None:
    reasons.append({"code": code, "severity": severity, "message": message})


def _classify(reasons: list[dict[str, str]]) -> str:
    severities = {reason["severity"] for reason in reasons}
    if "FAIL" in severities:
        return "FAIL"
    if "STALE" in severities:
        return "STALE"
    if "WARN" in severities:
        return "WARN"
    return "OK"


def _finalize_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    output = dict(receipt)
    output["receipt_sha256"] = canonical_sha256(output)
    return output


def _failure_receipt(
    checked_utc: str,
    error: CustodyError,
    *,
    policy_sha256: str | None = None,
) -> dict[str, Any]:
    return _finalize_receipt(
        {
            "schema": RECEIPT_SCHEMA,
            "classification": "FAIL",
            "custody_valid": False,
            "checked_utc": checked_utc,
            "snapshot_kind": "UNVERIFIED",
            "frozen_source": {
                "commit": None,
                "protocol_sha256": None,
                "runtime_sha256": None,
                "parent_v2_protocol_sha256": None,
                "bytes_verified": False,
                "commit_verified": False,
            },
            "watchdog": {
                "policy_sha256": policy_sha256,
                "verifier_sha256": _file_sha256(Path(__file__)),
                "network_access_used": False,
                "source_artifacts_mutated": False,
            },
            "counts": {
                "prediction_panels": 0,
                "settlement_panels": 0,
                "unsettled_panels": 0,
                "missing_prediction_periods": 0,
                "missing_settlement_periods": 0,
                "complete_utc_days": 0,
            },
            "sample_readiness": {
                key: False for key in sorted(SAMPLE_READINESS_FIELDS)
            },
            "freshness": {
                "status_age_seconds": None,
                "operational_receipt_age_seconds": None,
                "oldest_unsettled_lag_seconds": None,
            },
            "chain_terminals": {"prediction": ZERO_HASH, "settlement": ZERO_HASH},
            "reasons": [
                {
                    "code": error.code,
                    "severity": "FAIL",
                    "message": error.safe_message,
                }
            ],
            "automatic_promotion_allowed": False,
            "performance_evaluated": False,
            "performance_fields_exposed": False,
            "claim_boundary": (
                "Custody failure. No V3 score, model comparison, promotion, collection, "
                "prediction, settlement, release, or production conclusion is authorized."
            ),
        }
    )


def verify_snapshot(
    *,
    input_dir: Path,
    as_of_utc: str,
    policy_path: Path = DEFAULT_POLICY,
    source_root: Path | None = None,
) -> dict[str, Any]:
    checked = _parse_utc(as_of_utc, "as-of time")
    checked_text = checked.isoformat().replace("+00:00", "Z")
    policy_sha256: str | None = None
    try:
        policy, policy_sha256 = _load_policy(policy_path)
        input_dir = input_dir.resolve(strict=True)
        if not input_dir.is_dir() or input_dir.is_symlink():
            raise CustodyError("UNSAFE_INPUT_PATH", "input must be a regular directory")
        input_contract = policy["input_contract"]
        allowed_files = set(input_contract["files"])
        observed_files = {path.name for path in input_dir.iterdir()}
        if observed_files != allowed_files:
            raise CustodyError(
                "INPUT_ALLOWLIST_MISMATCH",
                "the input directory does not match the exact public-safe file allowlist",
            )
        maximum_bytes = input_contract["maximum_file_bytes"]
        maximum_records = input_contract["maximum_records_per_chain"]
        manifest = _read_json(input_dir / "manifest.json", "manifest", maximum_bytes)
        status = _read_json(input_dir / "status.json", "status", maximum_bytes)
        operational = _read_json(
            input_dir / "operational_receipt.json", "operational receipt", maximum_bytes
        )
        predictions = _read_jsonl(
            input_dir / "prediction_custody_panels.jsonl",
            "prediction custody chain",
            maximum_bytes,
            maximum_records,
        )
        settlements = _read_jsonl(
            input_dir / "settlement_custody_panels.jsonl",
            "settlement custody chain",
            maximum_bytes,
            maximum_records,
        )
        for value in (manifest, status, operational, predictions, settlements):
            _find_score_leak(value)

        _require_fields(manifest, MANIFEST_FIELDS, "MANIFEST_SCHEMA_MISMATCH")
        _require_fields(status, STATUS_FIELDS, "STATUS_SCHEMA_MISMATCH")
        _require_fields(
            operational,
            OPERATIONAL_RECEIPT_FIELDS,
            "OPERATIONAL_RECEIPT_SCHEMA_MISMATCH",
        )
        if manifest.get("schema") != input_contract["snapshot_schema"]:
            raise CustodyError("MANIFEST_SCHEMA_MISMATCH", "snapshot schema is not allowlisted")
        if status.get("schema") != input_contract["status_schema"]:
            raise CustodyError("STATUS_SCHEMA_MISMATCH", "status schema is not allowlisted")
        if operational.get("schema") != input_contract["operational_receipt_schema"]:
            raise CustodyError(
                "OPERATIONAL_RECEIPT_SCHEMA_MISMATCH",
                "operational receipt schema is not allowlisted",
            )
        if manifest.get("snapshot_kind") not in {
            "synthetic_public_safe_contract_fixture",
            "public_safe_custody_projection",
        }:
            raise CustodyError(
                "SNAPSHOT_KIND_NOT_ALLOWED", "snapshot kind is not public-safe and allowlisted"
            )
        frozen_manifest = manifest.get("frozen_source")
        expected_frozen = {
            "repository": policy["frozen_source"]["repository"],
            **_expected_identity(policy),
        }
        if not isinstance(frozen_manifest, dict) or frozen_manifest != expected_frozen:
            raise CustodyError(
                "SNAPSHOT_SOURCE_IDENTITY_MISMATCH",
                "the snapshot manifest is not bound to the frozen V3 source",
            )
        for value in (status, operational):
            _verify_identity(value, policy)
            _verify_boundary_flags(value)
        _verify_boundary_flags(manifest)

        descriptors = manifest.get("files")
        expected_descriptor_names = allowed_files - {"manifest.json"}
        if not isinstance(descriptors, dict) or set(descriptors) != expected_descriptor_names:
            raise CustodyError(
                "MANIFEST_FILE_SET_MISMATCH",
                "manifest file descriptors do not match the input allowlist",
            )
        for name, descriptor in descriptors.items():
            if not isinstance(descriptor, dict) or set(descriptor) != FILE_DESCRIPTOR_FIELDS:
                raise CustodyError(
                    "MANIFEST_FILE_DESCRIPTOR_MISMATCH",
                    "manifest file descriptor fields do not match",
                )
            path = input_dir / name
            expected_size = _require_int(
                descriptor.get("bytes"),
                "MANIFEST_FILE_DESCRIPTOR_MISMATCH",
                "manifest byte count must be a nonnegative integer",
            )
            expected_hash = _require_sha256(descriptor.get("sha256"))
            if path.stat().st_size != expected_size or _file_sha256(path) != expected_hash:
                raise CustodyError(
                    "MANIFEST_FILE_HASH_MISMATCH",
                    "a public-safe input file does not match its manifest descriptor",
                )

        source_verification = {
            "bytes_verified": False,
            "commit_verified": False,
            "artifact_count": 0,
        }
        if source_root is not None:
            source_verification = _verify_frozen_source(source_root, policy)

        prediction_terminal = _verify_chain(
            predictions,
            PREDICTION_FIELDS,
            input_contract["prediction_schema"],
            policy,
            "prediction",
        )
        settlement_terminal = _verify_chain(
            settlements,
            SETTLEMENT_FIELDS,
            input_contract["settlement_schema"],
            policy,
            "settlement",
        )
        prediction_by_target = {
            record["target_period_end_utc"]: record for record in predictions
        }
        settlement_targets = {
            record["target_period_end_utc"] for record in settlements
        }
        for settlement in settlements:
            target = settlement["target_period_end_utc"]
            prediction = prediction_by_target.get(target)
            if prediction is None:
                raise CustodyError(
                    "SETTLEMENT_WITHOUT_PREDICTION",
                    "a settlement panel has no matching prediction panel",
                )
            if (
                settlement["v3_prediction_panel_record_sha256"]
                != prediction["record_sha256"]
                or settlement["parent_v2_prediction_panel_record_sha256"]
                != prediction["parent_v2_prediction_panel_record_sha256"]
            ):
                raise CustodyError(
                    "SETTLEMENT_PREDICTION_BINDING_MISMATCH",
                    "a settlement panel is not bound to its matching prediction panel",
                )

        prediction_targets = set(prediction_by_target)
        complete_days = _complete_utc_days(settlement_targets)
        unsettled_targets = prediction_targets - settlement_targets
        missing_prediction_periods = _missing_prediction_period_count(
            prediction_targets,
            _parse_period(policy["protocol_contract"]["first_allowed_period_end_utc"]),
        )
        missing_settlement_periods = _missing_settlement_period_count(
            prediction_targets, settlement_targets
        )
        readiness = _sample_readiness(len(settlements), complete_days, policy)
        status_readiness = status.get("sample_readiness")
        if (
            not isinstance(status_readiness, dict)
            or set(status_readiness) != SAMPLE_READINESS_FIELDS
            or status_readiness != readiness
        ):
            raise CustodyError(
                "SAMPLE_READINESS_MISMATCH",
                "declared sample readiness does not match custody counts",
            )

        status_sha256 = canonical_sha256(status)
        expected_counts = {
            "prediction_panel_count": len(predictions),
            "settlement_panel_count": len(settlements),
            "complete_utc_day_count": complete_days,
            "unsettled_panel_count": len(unsettled_targets),
        }
        expected_terminals = {
            "prediction_terminal_sha256": prediction_terminal,
            "settlement_terminal_sha256": settlement_terminal,
        }
        for container in (manifest, status, operational):
            if any(container.get(key) != value for key, value in expected_counts.items()):
                raise CustodyError(
                    "COUNT_MISMATCH",
                    "manifest, status, or receipt counts do not match the custody chains",
                )
            if any(container.get(key) != value for key, value in expected_terminals.items()):
                raise CustodyError(
                    "TERMINAL_CHAIN_MISMATCH",
                    "manifest, status, or receipt terminal hashes do not match",
                )
        if (
            operational.get("status_sha256") != status_sha256
            or manifest.get("status_sha256") != status_sha256
        ):
            raise CustodyError(
                "STATUS_HASH_MISMATCH",
                "the status hash binding does not match the public-safe status",
            )

        manifest_generated = _parse_utc(manifest.get("generated_utc"), "manifest time")
        status_generated = _parse_utc(status.get("generated_utc"), "status time")
        receipt_generated = _parse_utc(operational.get("run_utc"), "receipt time")
        clock_skew = policy["classification_policy"][
            "maximum_future_clock_skew_seconds"
        ]
        for observed in (manifest_generated, status_generated, receipt_generated):
            if (observed - checked).total_seconds() > clock_skew:
                raise CustodyError(
                    "FUTURE_TIMESTAMP",
                    "a custody timestamp exceeds the permitted future clock skew",
                )
        status_age = max(0, int((checked - status_generated).total_seconds()))
        receipt_age = max(0, int((checked - receipt_generated).total_seconds()))
        oldest_unsettled_lag: int | None = None
        if unsettled_targets:
            oldest = min(_parse_period(value) for value in unsettled_targets)
            oldest_unsettled_lag = max(0, int((checked - oldest).total_seconds()))

        reasons: list[dict[str, str]] = []
        classification_policy = policy["classification_policy"]
        if status_age >= classification_policy["status_stale_after_seconds"]:
            _add_reason(
                reasons,
                "STATUS_STALE",
                "STALE",
                "public-safe status exceeds the frozen stale threshold",
            )
        elif status_age >= classification_policy["status_warn_after_seconds"]:
            _add_reason(
                reasons,
                "STATUS_AGING",
                "WARN",
                "public-safe status exceeds the frozen warning threshold",
            )
        if receipt_age >= classification_policy["receipt_stale_after_seconds"]:
            _add_reason(
                reasons,
                "OPERATIONAL_RECEIPT_STALE",
                "STALE",
                "operational receipt exceeds the frozen stale threshold",
            )
        elif receipt_age >= classification_policy["receipt_warn_after_seconds"]:
            _add_reason(
                reasons,
                "OPERATIONAL_RECEIPT_AGING",
                "WARN",
                "operational receipt exceeds the frozen warning threshold",
            )
        if missing_prediction_periods:
            _add_reason(
                reasons,
                "MISSING_PREDICTION_TARGET_PERIODS",
                classification_policy["missing_periods_classification"],
                f"{missing_prediction_periods} target periods are missing from the prediction chain",
            )
        if missing_settlement_periods:
            _add_reason(
                reasons,
                "MISSING_SETTLEMENT_TARGET_PERIODS",
                classification_policy["missing_periods_classification"],
                f"{missing_settlement_periods} earlier targets are missing from the settlement chain",
            )
        if len(unsettled_targets) >= classification_policy["unsettled_backlog_warn_count"]:
            _add_reason(
                reasons,
                "UNSETTLED_BACKLOG",
                "WARN",
                f"unsettled backlog reached {len(unsettled_targets)} panels",
            )
        if (
            oldest_unsettled_lag is not None
            and oldest_unsettled_lag
            >= classification_policy["unsettled_lag_warn_seconds"]
        ):
            _add_reason(
                reasons,
                "UNSETTLED_LAG",
                "WARN",
                "the oldest unsettled target exceeds the frozen lag threshold",
            )
        reasons.sort(key=lambda item: (item["severity"], item["code"]))
        classification = _classify(reasons)
        frozen = policy["frozen_source"]
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "classification": classification,
            "custody_valid": classification != "FAIL",
            "checked_utc": checked_text,
            "snapshot_kind": manifest["snapshot_kind"],
            "frozen_source": {
                "commit": frozen["commit"],
                "protocol_sha256": frozen["artifacts"]["protocol"]["sha256"],
                "runtime_sha256": frozen["artifacts"]["runtime"]["sha256"],
                "parent_v2_protocol_sha256": frozen["artifacts"][
                    "parent_v2_protocol"
                ]["sha256"],
                "bytes_verified": source_verification["bytes_verified"],
                "commit_verified": source_verification["commit_verified"],
            },
            "watchdog": {
                "policy_sha256": policy_sha256,
                "verifier_sha256": _file_sha256(Path(__file__)),
                "manifest_sha256": _file_sha256(input_dir / "manifest.json"),
                "network_access_used": False,
                "source_artifacts_mutated": False,
            },
            "counts": {
                "prediction_panels": len(predictions),
                "settlement_panels": len(settlements),
                "unsettled_panels": len(unsettled_targets),
                "missing_prediction_periods": missing_prediction_periods,
                "missing_settlement_periods": missing_settlement_periods,
                "complete_utc_days": complete_days,
            },
            "sample_readiness": readiness,
            "freshness": {
                "status_age_seconds": status_age,
                "operational_receipt_age_seconds": receipt_age,
                "oldest_unsettled_lag_seconds": oldest_unsettled_lag,
            },
            "chain_terminals": {
                "prediction": prediction_terminal,
                "settlement": settlement_terminal,
            },
            "reasons": reasons,
            "automatic_promotion_allowed": False,
            "performance_evaluated": False,
            "performance_fields_exposed": False,
            "claim_boundary": (
                "This receipt establishes only deterministic public-safe custody and "
                "operational checks. It does not compute or expose V3 scores or model "
                "comparisons and does not authorize promotion, collection changes, "
                "prediction, settlement, release, deployment, or production use."
            ),
        }
        return _finalize_receipt(receipt)
    except CustodyError as exc:
        return _failure_receipt(checked_text, exc, policy_sha256=policy_sha256)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        safe = CustodyError(
            "INTERNAL_WATCHDOG_ERROR",
            "the watchdog encountered an unexpected fail-closed input error",
        )
        return _failure_receipt(checked_text, safe, policy_sha256=policy_sha256)


def render_summary(receipt: dict[str, Any]) -> str:
    counts = receipt["counts"]
    freshness = receipt["freshness"]
    readiness = receipt["sample_readiness"]
    lines = [
        "# EIA V3 public-safe custody watchdog",
        "",
        f"- Classification: `{receipt['classification']}`",
        f"- Custody valid: `{str(receipt['custody_valid']).lower()}`",
        f"- Frozen source bytes verified: `{str(receipt['frozen_source']['bytes_verified']).lower()}`",
        f"- Prediction panels: `{counts['prediction_panels']}`",
        f"- Settlement panels: `{counts['settlement_panels']}`",
        f"- Unsettled panels: `{counts['unsettled_panels']}`",
        f"- Missing prediction periods: `{counts['missing_prediction_periods']}`",
        f"- Missing settlement periods: `{counts['missing_settlement_periods']}`",
        f"- Complete UTC days: `{counts['complete_utc_days']}`",
        f"- Status age seconds: `{freshness['status_age_seconds']}`",
        f"- Operational receipt age seconds: `{freshness['operational_receipt_age_seconds']}`",
        f"- 168-hour sample ready: `{str(readiness['operational_shakeout_168_hours']).lower()}`",
        f"- 720-hour sample ready: `{str(readiness['preliminary_720_hours']).lower()}`",
        f"- 2160-hour sample ready: `{str(readiness['confirmatory_2160_hours']).lower()}`",
        f"- 90-day sample ready: `{str(readiness['minimum_90_complete_utc_days']).lower()}`",
        "- Performance evaluated: `false`",
        "- Automatic promotion allowed: `false`",
        "",
        "## Reasons",
        "",
    ]
    if receipt["reasons"]:
        lines.extend(
            f"- `{reason['severity']}` `{reason['code']}`: {reason['message']}"
            for reason in receipt["reasons"]
        )
    else:
        lines.append("- No custody, freshness, gap, backlog, or lag exceptions.")
    lines.extend(["", receipt["claim_boundary"], ""])
    return "\n".join(lines)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--as-of-utc", required=True)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()
    receipt = verify_snapshot(
        input_dir=args.input_dir,
        as_of_utc=args.as_of_utc,
        policy_path=args.policy,
        source_root=args.source_root,
    )
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        _write_text(args.json_out, rendered)
    if args.summary_out:
        _write_text(args.summary_out, render_summary(receipt))
    print(rendered, end="")
    policy_success = {"OK", "WARN", "STALE"}
    return 0 if receipt["classification"] in policy_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
