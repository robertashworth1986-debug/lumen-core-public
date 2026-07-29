"""Build a fail-closed inventory and release gate for capability artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "capability_statement_governance_v1.json"
OUTPUT_JSON = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "CAPABILITY_ARTIFACT_GOVERNANCE_2026-07-26.json"
)
OUTPUT_MD = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "CAPABILITY_ARTIFACT_GOVERNANCE_2026-07-26.md"
)
SCHEMA = "lumencore.capability_statement_governance.v1"
CONFIG_SCHEMA = "lumencore.capability_statement_governance_config.v1"
EXPECTED_CONTROLS = {
    "action_time_human_approval_required": True,
    "autonomous_email_send_allowed": False,
    "autonomous_submission_allowed": False,
    "closed_route_reuse_allowed": False,
    "duplicate_suppression_required": True,
    "evidence_snapshot_refresh_required": True,
    "performance_claims_require_independent_evidence": True,
    "unregistered_capability_artifact_blocks_release": True,
}
ALLOWED_STATUSES = {
    "HISTORICAL_DO_NOT_SEND",
    "CLOSED_ROUTE_DO_NOT_SEND",
    "DOMAIN_BOUNDARY_REUSE_REQUIRES_CURRENT_SOURCE_RECHECK",
    "CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED",
}


class GovernanceError(ValueError):
    """Raised when a capability-governance invariant is violated."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError(f"Unreadable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise GovernanceError(f"Expected an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical_sha256(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()


def parse_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GovernanceError(f"{label} must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GovernanceError(f"{label} is invalid") from exc
    return parsed.astimezone(timezone.utc)


def normalize(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA or config.get("version") != 1:
        raise GovernanceError("Unsupported capability-governance config")
    if config.get("controls") != EXPECTED_CONTROLS:
        raise GovernanceError("Capability controls are not fail-closed")
    discovery = config.get("discovery")
    if not isinstance(discovery, dict):
        raise GovernanceError("discovery must be an object")
    if not discovery.get("roots") or not discovery.get("filename_markers"):
        raise GovernanceError("discovery roots and markers are required")
    artifacts = config.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise GovernanceError("artifacts must be a nonempty list")
    ids: set[str] = set()
    paths: set[str] = set()
    for index, artifact in enumerate(artifacts):
        label = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            raise GovernanceError(f"{label} must be an object")
        artifact_id = artifact.get("id")
        path = artifact.get("path")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise GovernanceError(f"{label}.id is required")
        if not isinstance(path, str) or not path:
            raise GovernanceError(f"{label}.path is required")
        if artifact_id in ids or path in paths:
            raise GovernanceError("Duplicate capability artifact id or path")
        ids.add(artifact_id)
        paths.add(path)
        if artifact.get("status") not in ALLOWED_STATUSES:
            raise GovernanceError(f"{label}.status is invalid")
        if artifact.get("deadline_utc"):
            parse_utc(artifact["deadline_utc"], f"{label}.deadline_utc")
        markers = artifact.get("required_text_markers")
        if not isinstance(markers, list) or not all(
            isinstance(marker, str) and marker for marker in markers
        ):
            raise GovernanceError(f"{label}.required_text_markers is invalid")
    if not config.get("claim_boundary"):
        raise GovernanceError("claim_boundary is required")


def discover_capability_artifacts(config: dict[str, Any]) -> list[str]:
    markers = config["discovery"]["filename_markers"]
    discovered: set[str] = set()
    for root_name in config["discovery"]["roots"]:
        root = ROOT / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and any(marker in path.name for marker in markers):
                discovered.add(normalize(path))
    return sorted(discovered)


def build_registry(
    config_path: Path = CONFIG_PATH,
    *,
    as_of_utc: str,
) -> dict[str, Any]:
    config = read_json(config_path)
    validate_config(config)
    now = parse_utc(as_of_utc, "as_of_utc")
    registered_paths = {artifact["path"] for artifact in config["artifacts"]}
    discovered_paths = set(discover_capability_artifacts(config))
    unregistered = sorted(discovered_paths - registered_paths)

    records: list[dict[str, Any]] = []
    missing_artifacts: list[str] = []
    marker_failures: list[str] = []
    missing_dependencies: list[str] = []
    for artifact in config["artifacts"]:
        path = ROOT / artifact["path"]
        if not path.is_file():
            missing_artifacts.append(artifact["path"])
            continue
        missing_markers: list[str] = []
        if artifact["required_text_markers"]:
            text = path.read_text(encoding="utf-8")
            missing_markers = [
                marker
                for marker in artifact["required_text_markers"]
                if marker not in text
            ]
            if missing_markers:
                marker_failures.append(artifact["path"])
        dependency_receipts = []
        for dependency in artifact.get("dependencies", []):
            dependency_path = ROOT / dependency
            if not dependency_path.is_file():
                missing_dependencies.append(dependency)
                continue
            dependency_receipts.append(
                {
                    "path": dependency,
                    "bytes": dependency_path.stat().st_size,
                    "sha256": sha256_file(dependency_path),
                }
            )
        deadline_closed = False
        if artifact.get("deadline_utc"):
            deadline_closed = parse_utc(
                artifact["deadline_utc"], "deadline_utc"
            ) <= now
        records.append(
            {
                **artifact,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "deadline_closed": deadline_closed,
                "missing_text_markers": missing_markers,
                "dependencies": dependency_receipts,
                "external_release_authorized": False,
                "send_eligible": False,
            }
        )

    blockers = {
        "missing_artifacts": sorted(set(missing_artifacts)),
        "unregistered_artifacts": unregistered,
        "marker_failures": sorted(set(marker_failures)),
        "missing_dependencies": sorted(set(missing_dependencies)),
    }
    blocked = any(blockers.values())
    summary = {
        "registered_artifact_count": len(config["artifacts"]),
        "verified_artifact_count": len(records),
        "current_public_safe_count": sum(
            row["status"] == "CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED"
            for row in records
        ),
        "historical_or_closed_count": sum(
            row["status"] in {"HISTORICAL_DO_NOT_SEND", "CLOSED_ROUTE_DO_NOT_SEND"}
            for row in records
        ),
        "domain_boundary_refresh_count": sum(
            row["status"]
            == "DOMAIN_BOUNDARY_REUSE_REQUIRES_CURRENT_SOURCE_RECHECK"
            for row in records
        ),
        "external_release_authorized_count": 0,
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "status": (
            "CAPABILITY_ARTIFACT_GOVERNANCE_BLOCKED"
            if blocked
            else "GOVERNED_CURRENT_PACKET_WITH_ARCHIVED_LEGACY"
        ),
        "as_of_utc": as_of_utc,
        "summary": summary,
        "controls": config["controls"],
        "blockers": blockers,
        "artifacts": records,
        "safest_next_action": (
            "Resolve every missing, unregistered, or unmarked capability artifact before external reuse."
            if blocked
            else "Use only the current public-safe PDF after notice-specific claim, duplicate, and action-time human review; keep historical and closed-route files internal."
        ),
        "claim_boundary": config["claim_boundary"],
        "control_sha256": "",
    }
    payload["control_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "control_sha256"}
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Capability Statement Governance",
        "",
        f"- As of UTC: `{payload['as_of_utc']}`",
        f"- Status: `{payload['status']}`",
        f"- Registered artifacts: `{payload['summary']['registered_artifact_count']}`",
        f"- Current public-safe artifacts: `{payload['summary']['current_public_safe_count']}`",
        f"- Historical or closed artifacts: `{payload['summary']['historical_or_closed_count']}`",
        f"- External releases authorized: `{payload['summary']['external_release_authorized_count']}`",
        f"- Control SHA-256: `{payload['control_sha256']}`",
        "",
        "## Artifact Register",
        "",
        "| Artifact | Status | Deadline closed | Release | SHA-256 |",
        "|---|---|---:|---:|---|",
    ]
    for row in payload["artifacts"]:
        lines.append(
            f"| `{row['path']}` | `{row['status']}` | "
            f"`{str(row['deadline_closed']).lower()}` | "
            f"`{str(row['external_release_authorized']).lower()}` | "
            f"`{row['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Safest Next Action",
            "",
            payload["safest_next_action"],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--as-of-utc",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_registry(as_of_utc=args.as_of_utc)
    if not args.check:
        write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "registered_artifact_count": payload["summary"][
                    "registered_artifact_count"
                ],
                "current_public_safe_count": payload["summary"][
                    "current_public_safe_count"
                ],
                "historical_or_closed_count": payload["summary"][
                    "historical_or_closed_count"
                ],
                "unregistered_artifact_count": len(
                    payload["blockers"]["unregistered_artifacts"]
                ),
                "external_release_authorized_count": payload["summary"][
                    "external_release_authorized_count"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if payload["status"] != "CAPABILITY_ARTIFACT_GOVERNANCE_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
