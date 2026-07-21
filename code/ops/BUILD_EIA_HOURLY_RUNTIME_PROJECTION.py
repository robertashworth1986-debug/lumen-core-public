from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_RELATIVE = Path("config/eia_grid_prospective_hourly_router_protocol_v1.json")
STATUS_RELATIVE = Path("out/eia_grid_prospective_hourly_router/prospective_status_latest.json")
CYCLE_RELATIVE = Path("out/eia_grid_prospective_hourly_router/latest_cycle.json")
OUTPUT_RELATIVE = Path(
    "evidence/external_validation/eia_grid_prospective_hourly_runtime_projection_20260716.json"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PRIVATE_PATTERNS = (
    re.compile(r"[A-Za-z]:[/\\]Users[/\\]", re.I),
    re.compile(r"private_estate", re.I),
    re.compile(r"cp575notice", re.I),
    re.compile(r"(?:api|access|refresh|client)[_-]?(?:key|token|secret)\s*[:=]", re.I),
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_dict(payload: dict[str, Any], key: str, source: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{source}.{key} must be an object")
    return value


def require_bool(payload: dict[str, Any], key: str, source: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{source}.{key} must be boolean")
    return value


def require_nonnegative_int(payload: dict[str, Any], key: str, source: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{source}.{key} must be a non-negative integer")
    return value


def require_number(payload: dict[str, Any], key: str, source: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{source}.{key} must be numeric")
    return float(value)


def require_string(payload: dict[str, Any], key: str, source: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source}.{key} must be a non-empty string")
    return value


def require_sha256(payload: dict[str, Any], key: str, source: str) -> str:
    value = require_string(payload, key, source).casefold()
    if not SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{source}.{key} must be a lowercase SHA-256 digest")
    return value


def assert_public_safe(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, sort_keys=True, default=str)
    hits = [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(text)]
    if hits:
        raise ValueError(f"runtime projection failed public-safety scan: {hits}")


def validate_public_projection(
    projection: dict[str, Any],
    protocol: dict[str, Any],
    *,
    protocol_sha256: str,
) -> None:
    if projection.get("schema") != "eia_grid_prospective_hourly_runtime_projection.v1":
        raise ValueError("unexpected public projection schema")
    projected_protocol = require_dict(projection, "protocol", "projection")
    if require_string(projected_protocol, "protocol_id", "projection.protocol") != require_string(
        protocol,
        "protocol_id",
        "protocol",
    ):
        raise ValueError("public projection protocol id does not match")
    if require_sha256(projected_protocol, "sha256", "projection.protocol") != protocol_sha256:
        raise ValueError("public projection protocol hash does not match")

    integrity = require_dict(projection, "integrity", "projection")
    if require_bool(integrity, "gate_passed", "projection.integrity") is not True:
        raise ValueError("public projection integrity gate is closed")
    checks = require_dict(integrity, "checks", "projection.integrity")
    if not checks or any(value is not True for value in checks.values()):
        raise ValueError("public projection integrity checks must all pass")

    sample = require_dict(projection, "sample_state", "projection")
    common_hours = require_nonnegative_int(
        sample,
        "common_settled_hour_count",
        "projection.sample_state",
    )
    require_nonnegative_int(sample, "prediction_count", "projection.sample_state")
    require_nonnegative_int(sample, "settlement_count", "projection.sample_state")
    window = require_dict(protocol, "prospective_window", "protocol")
    readiness = (
        ("preliminary_ready", "preliminary_gate_common_hours_per_authority"),
        ("confirmatory_ready", "confirmatory_gate_common_hours_per_authority"),
        ("durability_ready", "durability_gate_common_hours_per_authority"),
    )
    for readiness_key, threshold_key in readiness:
        threshold = require_nonnegative_int(window, threshold_key, "protocol.prospective_window")
        ready = require_bool(sample, readiness_key, "projection.sample_state")
        if ready != (common_hours >= threshold):
            raise ValueError(f"public projection {readiness_key} does not reconcile")
    if require_bool(
        sample,
        "promotion_evaluation_complete",
        "projection.sample_state",
    ) and not require_bool(sample, "confirmatory_ready", "projection.sample_state"):
        raise ValueError("public projection promotion evaluation is premature")

    snapshot = require_dict(projection, "runtime_snapshot", "projection")
    require_sha256(snapshot, "status_sha256", "projection.runtime_snapshot")
    require_sha256(snapshot, "cycle_sha256", "projection.runtime_snapshot")
    if require_bool(
        snapshot,
        "raw_runtime_in_public_repository",
        "projection.runtime_snapshot",
    ):
        raise ValueError("raw private runtime may not be represented as public")
    chains = require_dict(projection, "chain_receipts", "projection")
    for key in (
        "operational_receipt_sha256",
        "prediction_terminal_sha256",
        "settlement_terminal_sha256",
        "source_panel_row_chain_sha256",
    ):
        require_sha256(chains, key, "projection.chain_receipts")
    assert_public_safe(projection)


def build_projection(*, root: Path = ROOT) -> dict[str, Any]:
    protocol_path = root / PROTOCOL_RELATIVE
    status_path = root / STATUS_RELATIVE
    cycle_path = root / CYCLE_RELATIVE
    protocol = read_json(protocol_path)
    status = read_json(status_path)
    cycle = read_json(cycle_path)
    receipt = require_dict(cycle, "operational_receipt", "latest_cycle")
    cycle_status = require_dict(cycle, "status", "latest_cycle")
    sample_gates = require_dict(status, "sample_gates", "status")
    fixed_scores = require_dict(
        status,
        "fixed_candidate_mean_scaled_absolute_error",
        "status",
    )

    if protocol.get("schema") != "eia_grid_prospective_hourly_router_protocol.v1":
        raise ValueError("unexpected hourly protocol schema")
    if status.get("schema") != "eia_grid_prospective_hourly_router_status.v1":
        raise ValueError("unexpected hourly status schema")
    if cycle.get("schema") != "eia_grid_prospective_hourly_router_cycle.v1":
        raise ValueError("unexpected hourly cycle schema")
    if receipt.get("schema") != "eia_grid_prospective_hourly_router_operational_run.v1":
        raise ValueError("unexpected hourly operational-receipt schema")
    if cycle_status != status:
        raise ValueError("latest cycle status does not match the published runtime status")

    protocol_sha256 = sha256_file(protocol_path)
    prediction_count = require_nonnegative_int(status, "prediction_count", "status")
    settlement_count = require_nonnegative_int(status, "settlement_count", "status")
    common_settled_hours = require_nonnegative_int(
        status,
        "common_settled_hour_count",
        "status",
    )
    best_fixed = require_string(status, "current_best_fixed_candidate", "status")
    if best_fixed not in fixed_scores:
        raise ValueError("current best fixed candidate is absent from the fixed score table")

    checks = {
        "protocol_identity_matched": (
            require_sha256(status, "protocol_sha256", "status") == protocol_sha256
            and require_sha256(receipt, "protocol_sha256", "operational_receipt")
            == protocol_sha256
        ),
        "protocol_commit_matched": (
            require_string(status, "protocol_commit", "status")
            == require_string(receipt, "protocol_commit", "operational_receipt")
        ),
        "prediction_count_reconciled": (
            prediction_count
            == require_nonnegative_int(receipt, "prediction_count", "operational_receipt")
        ),
        "settlement_count_reconciled": (
            settlement_count
            == require_nonnegative_int(receipt, "settlement_count", "operational_receipt")
        ),
        "operational_receipt_reconciled": (
            require_sha256(status, "operational_receipt_sha256", "status")
            == require_sha256(receipt, "record_sha256", "operational_receipt")
        ),
        "prediction_terminal_hash_valid": bool(
            SHA256_PATTERN.fullmatch(
                require_sha256(receipt, "prediction_terminal_sha256", "operational_receipt")
            )
        ),
        "settlement_terminal_hash_valid": bool(
            SHA256_PATTERN.fullmatch(
                require_sha256(receipt, "settlement_terminal_sha256", "operational_receipt")
            )
        ),
        "source_panel_chain_hash_valid": bool(
            SHA256_PATTERN.fullmatch(
                require_sha256(receipt, "source_panel_row_chain_sha256", "operational_receipt")
            )
        ),
    }
    protocol_commit = require_string(status, "protocol_commit", "status").casefold()
    if not COMMIT_PATTERN.fullmatch(protocol_commit):
        raise ValueError("status.protocol_commit must be a lowercase 40-character Git commit")
    if not all(checks.values()):
        failed = sorted(key for key, passed in checks.items() if not passed)
        raise ValueError(f"hourly runtime projection integrity checks failed: {failed}")

    projection = {
        "schema": "eia_grid_prospective_hourly_runtime_projection.v1",
        "projected_from_status_generated_utc": require_string(
            status,
            "generated_utc",
            "status",
        ),
        "state": require_string(status, "state", "status"),
        "protocol": {
            "protocol_id": require_string(protocol, "protocol_id", "protocol"),
            "path": PROTOCOL_RELATIVE.as_posix(),
            "sha256": protocol_sha256,
            "commit": protocol_commit,
        },
        "runtime_snapshot": {
            "status_sha256": sha256_file(status_path),
            "cycle_sha256": sha256_file(cycle_path),
            "raw_runtime_in_public_repository": False,
        },
        "sample_state": {
            "prediction_count": prediction_count,
            "settlement_count": settlement_count,
            "common_settled_hour_count": common_settled_hours,
            "first_common_settled_period": status.get("first_common_settled_period"),
            "latest_common_settled_period": status.get("latest_common_settled_period"),
            "preliminary_ready": require_bool(sample_gates, "preliminary_ready", "sample_gates"),
            "confirmatory_ready": require_bool(sample_gates, "confirmatory_ready", "sample_gates"),
            "durability_ready": require_bool(sample_gates, "durability_ready", "sample_gates"),
            "promotion_evaluation_complete": require_bool(
                status,
                "promotion_evaluation_complete",
                "status",
            ),
        },
        "descriptive_metrics": {
            "current_best_fixed_candidate": best_fixed,
            "router_mean_scaled_absolute_error": require_number(
                status,
                "router_mean_scaled_absolute_error",
                "status",
            ),
            "best_fixed_mean_scaled_absolute_error": float(fixed_scores[best_fixed]),
            "router_skill_vs_current_best_fixed": require_number(
                status,
                "router_skill_vs_current_best_fixed",
                "status",
            ),
            "sample_gate_open": False,
            "interpretation": "Descriptive incomplete-sample values only; no promotion or external-generalization claim is allowed.",
        },
        "chain_receipts": {
            "operational_receipt_sha256": require_sha256(
                receipt,
                "record_sha256",
                "operational_receipt",
            ),
            "prediction_terminal_sha256": require_sha256(
                receipt,
                "prediction_terminal_sha256",
                "operational_receipt",
            ),
            "settlement_terminal_sha256": require_sha256(
                receipt,
                "settlement_terminal_sha256",
                "operational_receipt",
            ),
            "source_panel_row_chain_sha256": require_sha256(
                receipt,
                "source_panel_row_chain_sha256",
                "operational_receipt",
            ),
            "source_panel_row_count": require_nonnegative_int(
                receipt,
                "source_panel_row_count",
                "operational_receipt",
            ),
        },
        "integrity": {
            "gate_passed": True,
            "checks": checks,
            "configured_private_pattern_hit_count": 0,
        },
        "claim_boundary": require_string(status, "claim_boundary", "status"),
    }
    validate_public_projection(
        projection,
        protocol,
        protocol_sha256=protocol_sha256,
    )
    return projection


def resolve_output_path(*, root: Path, output: Path) -> Path:
    root = root.resolve()
    target = output.resolve() if output.is_absolute() else (root / output).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("public projection output must remain inside the repository") from exc
    return target


def write_projection(
    payload: dict[str, Any],
    *,
    root: Path = ROOT,
    output: Path = OUTPUT_RELATIVE,
) -> Path:
    target = resolve_output_path(root=root, output=output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project the private EIA hourly runtime into a public-safe reviewer snapshot."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_RELATIVE,
        help="Repository-relative immutable projection path to write or check.",
    )
    args = parser.parse_args()
    projection = build_projection()
    target = resolve_output_path(root=ROOT, output=args.output)
    expected = json.dumps(projection, indent=2, sort_keys=True) + "\n"
    published_current = target.is_file() and target.read_text(encoding="utf-8") == expected
    if not args.check:
        write_projection(projection, output=args.output)
        published_current = True
    print(
        json.dumps(
            {
                "integrity_gate_passed": projection["integrity"]["gate_passed"],
                "prediction_count": projection["sample_state"]["prediction_count"],
                "settlement_count": projection["sample_state"]["settlement_count"],
                "common_settled_hour_count": projection["sample_state"][
                    "common_settled_hour_count"
                ],
                "published_current": published_current,
                "output": target.relative_to(ROOT.resolve()).as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if published_current else 1


if __name__ == "__main__":
    raise SystemExit(main())
