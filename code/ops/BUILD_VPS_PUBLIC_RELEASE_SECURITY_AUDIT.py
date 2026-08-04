"""Build a privacy-preserving, read-only VPS and public-release audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
CANARY = ROOT / "out" / "ops" / "public_reviewer_release_canary_latest.json"
HYGIENE_GATE = ROOT / "out" / "ops" / "release_scope_hygiene_gate_latest.json"
INDEX_HYGIENE_GATE = (
    ROOT / "out" / "ops" / "release_scope_git_index_hygiene_gate_latest.json"
)
RELEASE_PLAN = (
    ROOT / "out" / "ops" / "PUBLIC_RELEASE_SYNC_PLAN_READY_2026-08-02.json"
)
FULL_RELEASE_PLAN = ROOT / "out" / "ops" / "PUBLIC_RELEASE_SYNC_PLAN_2026-07-18.json"
GATEWAY_MODULE = ROOT / "code" / "booth_public_contract.py"
GATEWAY_REPAIR = ROOT / "deploy" / "REPAIR_LUMA_GATEWAY_MODULE.ps1"
OUT_JSON = ROOT / "out" / "ops" / "vps_public_release_security_audit_20260802.json"
OUT_MD = ROOT / "docs" / "VPS_PUBLIC_RELEASE_SECURITY_AUDIT_2026-08-02.md"
OUT_LATEST_JSON = ROOT / "out" / "ops" / "vps_public_release_security_audit_latest.json"
OUT_LATEST_MD = ROOT / "docs" / "VPS_PUBLIC_RELEASE_SECURITY_AUDIT_CURRENT.md"

TRANSPORT_SCRIPTS = (
    ROOT / "deploy" / "PUSH_TO_VPS.ps1",
    ROOT / "deploy" / "PUSH_PROOF_FEEDS_TO_VPS.ps1",
    ROOT / "deploy" / "REPAIR_LUMA_GATEWAY_MODULE.ps1",
    ROOT / "code" / "ops" / "UPLOAD_TO_ORACLE.ps1",
)

ALLOWED_LOCAL_STAGE_ACTIONS = {
    "PLAN_NEW_LOCAL_STAGE_COPY",
    "NOOP_EXACT_MATCH",
}

CLAIM_BOUNDARY = (
    "This audit records local receipt state, public GET canary metadata, and deployment-script "
    "control signals. It does not prove security certification, uptime, scientific performance, "
    "external validation, agency approval, publication, deployment, or commercial acceptance."
)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generated_utc(value: str | None = None) -> str:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def audit_transport_script(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    lowered = text.lower()
    ipv4_values = re.findall(
        r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])", text
    )
    hardcoded_ipv4_count = sum(
        value not in {"127.0.0.1", "0.0.0.0"} for value in ipv4_values
    )
    machine_key_candidate_count = len(
        re.findall(r"downloads[\\/][^\s\"']+", lowered)
    )
    strict_yes = "stricthostkeychecking=yes" in lowered
    strict_no = "stricthostkeychecking=no" in lowered
    blockers: list[str] = []
    if not path.is_file():
        blockers.append("SCRIPT_MISSING")
    if strict_no:
        blockers.append("SSH_HOST_VERIFICATION_DISABLED")
    if not strict_yes:
        blockers.append("STRICT_HOST_VERIFICATION_NOT_EXPLICIT")
    if hardcoded_ipv4_count:
        blockers.append("HARDCODED_INFRASTRUCTURE_IDENTIFIER_PRESENT")
    if machine_key_candidate_count:
        blockers.append("MACHINE_SPECIFIC_KEY_DISCOVERY_PRESENT")
    if "human_unlock" not in lowered:
        blockers.append("HUMAN_UNLOCK_GATE_NOT_DETECTED")

    return {
        "path": relative(path),
        "exists": path.is_file(),
        "sha256": file_sha256(path),
        "host_from_environment_supported": "luma_vps_host" in lowered,
        "human_unlock_gate_detected": "human_unlock" in lowered,
        "strict_host_key_checking_yes_detected": strict_yes,
        "strict_host_key_checking_no_detected": strict_no,
        "hardcoded_ipv4_count": hardcoded_ipv4_count,
        "machine_specific_key_candidate_count": machine_key_candidate_count,
        "blockers": blockers,
        "transport_hardening_passed": not blockers,
    }


def release_candidates(plan: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for item in plan.get("items", []):
        if not isinstance(item, dict):
            continue
        blockers = [str(value) for value in item.get("blockers", [])]
        row = {
            "id": item.get("id"),
            "source_path": item.get("source_path"),
            "target_path": item.get("target_path"),
            "planned_action": item.get("planned_action"),
            "claim_state": item.get("claim_state"),
            "source_sha256": item.get("source_sha256"),
            "blockers": blockers,
            "external_action_allowed": False,
        }
        if not blockers and item.get("planned_action") in ALLOWED_LOCAL_STAGE_ACTIONS:
            row["status"] = "BOUNDED_CANDIDATE_AFTER_GLOBAL_GATES"
            candidates.append(row)
        else:
            row["status"] = "BLOCKED"
            blocked.append(row)
    return candidates, blocked


def build_audit(*, as_of_utc: str | None = None) -> dict[str, Any]:
    canary = read_json(CANARY)
    hygiene = read_json(HYGIENE_GATE)
    index_hygiene = read_json(INDEX_HYGIENE_GATE)
    plan = read_json(RELEASE_PLAN)
    full_plan = read_json(FULL_RELEASE_PLAN)
    candidates, candidate_plan_blocked_artifacts = release_candidates(plan)
    _, deferred_artifacts = release_candidates(full_plan)
    transport = [audit_transport_script(path) for path in TRANSPORT_SCRIPTS]

    canary_summary = canary.get("summary", {})
    plan_summary = plan.get("summary", {})
    hygiene_summary = hygiene.get("summary", {})
    hygiene_binding = hygiene.get("scope_binding", {})
    index_hygiene_summary = index_hygiene.get("summary", {})
    endpoint_rows = []
    for endpoint in canary.get("endpoints", []):
        if not isinstance(endpoint, dict):
            continue
        endpoint_rows.append(
            {
                "endpoint_id": endpoint.get("endpoint_id"),
                "status": endpoint.get("status"),
                "observed_status_code": endpoint.get("observed_status_code"),
                "observed_mime_type": endpoint.get("observed_mime_type"),
                "fetch_error": endpoint.get("fetch_error"),
                "failed_checks": endpoint.get("failed_checks", []),
                "response_body_recorded": False,
            }
        )

    transport_hardened = all(row["transport_hardening_passed"] for row in transport)
    blockers: list[str] = []
    if canary_summary.get("status") != "PASS":
        blockers.append("PUBLIC_REVIEWER_CANARY_BLOCKED")
    if plan_summary.get("plan_state") != "DRY_RUN_READY_HUMAN_UNLOCK_REQUIRED":
        blockers.append("PUBLIC_RELEASE_PLAN_BLOCKED")
    if (
        not hygiene_summary.get("release_scope_claim_allowed")
        or hygiene.get("mode") != "LOCAL_READ_ONLY_RELEASE_STAGE_OBSERVER"
        or hygiene_binding.get("plan_sha256") != plan.get("plan_sha256")
    ):
        blockers.append("RELEASE_STAGE_HYGIENE_OR_BINDING_BLOCKED")
    if not transport_hardened:
        blockers.append("DEPLOY_TRANSPORT_HARDENING_REQUIRED")
    blockers.extend(
        [
            "GATEWAY_REPAIR_NOT_VERIFIED_APPLIED",
            "ACTION_TIME_HUMAN_UNLOCK_REQUIRED",
        ]
    )

    module_hash = file_sha256(GATEWAY_MODULE)
    module_bytes = GATEWAY_MODULE.stat().st_size if GATEWAY_MODULE.is_file() else 0
    repair_script_hash = file_sha256(GATEWAY_REPAIR)
    exact_approval_text = (
        "APPROVE ONE VPS GATEWAY MODULE REPAIR NOW: "
        f"module SHA-256 {module_hash}; "
        f"repair script SHA-256 {repair_script_hash}; "
        "target service luma-gateway; install only the missing booth_public_contract.py "
        "or no-op on an exact match; no DNS, reverse-proxy, proof-feed, publication, "
        "scheduler, or unrelated deployment changes."
        if module_hash and repair_script_hash
        else None
    )
    audit: dict[str, Any] = {
        "schema": "lumencore.vps_public_release_security_audit.v1",
        "generated_utc": generated_utc(as_of_utc),
        "mode": "READ_ONLY_LOCAL_AND_PUBLIC_GET_METADATA",
        "summary": {
            "status": "BLOCKED",
            "public_release_allowed": False,
            "vps_mutation_allowed": False,
            "candidate_artifact_count": len(candidates),
            "candidate_plan_blocked_artifact_count": len(
                candidate_plan_blocked_artifacts
            ),
            "deferred_full_plan_artifact_count": len(deferred_artifacts),
            "blocked_artifact_count": len(deferred_artifacts),
            "public_endpoint_passed_count": canary_summary.get("passed_count", 0),
            "public_endpoint_count": canary_summary.get("endpoint_count", 0),
            "transport_script_passed_count": sum(
                row["transport_hardening_passed"] for row in transport
            ),
            "transport_script_count": len(transport),
        },
        "blockers": blockers,
        "public_canary": {
            "receipt_sha256": canary.get("receipt_sha256"),
            "status": canary_summary.get("status", "MISSING"),
            "endpoints": endpoint_rows,
        },
        "release_scope_hygiene": {
            "gate_sha256": hygiene.get("gate_sha256"),
            "mode": hygiene.get("mode", "MISSING"),
            "status": hygiene_summary.get("status", "MISSING"),
            "staged_path_count": hygiene_summary.get("staged_path_count"),
            "prohibited_staged_path_count": hygiene_summary.get(
                "prohibited_staged_path_count"
            ),
            "hash_verified_path_count": hygiene_summary.get(
                "hash_verified_path_count"
            ),
            "plan_sha256": hygiene_binding.get("plan_sha256"),
            "stage_manifest_sha256": hygiene_binding.get(
                "stage_manifest_sha256"
            ),
            "plan_binding_matches": (
                hygiene_binding.get("plan_sha256") == plan.get("plan_sha256")
            ),
            "path_names_recorded": False,
        },
        "repository_index_hygiene": {
            "gate_sha256": index_hygiene.get("gate_sha256"),
            "mode": index_hygiene.get("mode", "MISSING"),
            "status": index_hygiene_summary.get("status", "MISSING"),
            "staged_path_count": index_hygiene_summary.get("staged_path_count"),
            "prohibited_staged_path_count": index_hygiene_summary.get(
                "prohibited_staged_path_count"
            ),
            "release_scope_claim_allowed": index_hygiene_summary.get(
                "release_scope_claim_allowed", False
            ),
            "affects_isolated_release_stage": False,
            "path_names_recorded": False,
            "boundary": (
                "This separately records the broad repository index. It is not the sealed "
                "release stage and must not be used as a publication source."
            ),
        },
        "release_plan": {
            "plan_sha256": plan.get("plan_sha256"),
            "plan_state": plan_summary.get("plan_state", "MISSING"),
            "partial_release": plan.get("selection_scope", {}).get(
                "partial_release"
            ),
            "bounded_candidates_after_global_gates": candidates,
            "candidate_plan_blocked_artifacts": candidate_plan_blocked_artifacts,
            "deferred_full_plan_artifacts": deferred_artifacts,
            "blocked_artifacts": deferred_artifacts,
            "full_plan_sha256": full_plan.get("plan_sha256"),
            "external_action_allowed": False,
        },
        "gateway_repair_candidate": {
            "status": (
                "BOUNDED_REPAIR_PREPARED_ACTION_TIME_APPROVAL_REQUIRED"
                if GATEWAY_MODULE.is_file() and GATEWAY_REPAIR.is_file()
                else "REPAIR_INPUT_MISSING"
            ),
            "module_path": relative(GATEWAY_MODULE),
            "module_sha256": module_hash,
            "module_bytes": module_bytes,
            "repair_script_path": relative(GATEWAY_REPAIR),
            "repair_script_sha256": repair_script_hash,
            "required_exact_approval_text": exact_approval_text,
            "human_unlock_instruction": (
                "Configure the private LUMA_HUMAN_UNLOCK_TOKEN outside chat at action time; "
                "never include its value in the approval text or audit."
            ),
            "apply_allowed": False,
            "boundary": (
                "The prepared repair is limited to an exact-hash module upload and luma-gateway restart, "
                "but this audit does not authorize or prove that remote mutation."
            ),
        },
        "deployment_transport_audit": transport,
        "privacy_controls": {
            "credentials_accessed": False,
            "credential_values_recorded": False,
            "host_values_recorded": False,
            "key_filenames_recorded": False,
            "response_bodies_recorded": False,
            "remote_mutation_performed": False,
            "publication_performed": False,
        },
        "safest_next_action": (
            "Keep publication blocked. After exact action-time approval, apply only the sealed gateway-module "
            "repair and rerun the four-endpoint canary. If all endpoints pass, publish only the exact "
            "manifest-bound three-item stage, never the broad repository index; "
            + (
                "preserve the currently passing SSH host-verification controls, "
                if transport_hardened
                else "harden SSH host verification, "
            )
            + "keep the three PDFs deferred until clean-HEAD receipts pass, and require a fresh "
            "HumanUnlock before any publication."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    audit["audit_sha256"] = canonical_sha256(audit)
    return audit


def render_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    transport_hardened = (
        summary["transport_script_passed_count"] == summary["transport_script_count"]
    )
    transport_clause = (
        "deployment transport controls pass the local static audit"
        if transport_hardened
        else "deployment transport hardening remains incomplete"
    )
    lines = [
        "# VPS And Public-Release Security Audit",
        "",
        f"Generated UTC: `{audit['generated_utc']}`",
        f"Status: `{summary['status']}`",
        "",
        f"> {audit['claim_boundary']}",
        "",
        "## Decision",
        "",
        "Keep publication and VPS mutation blocked. The current public canary fails, "
        "the gateway repair is not verified applied, and action-time HumanUnlock remains "
        f"required. The isolated three-item stage passes hygiene; {transport_clause}.",
        "",
        "## Public Canary",
        "",
        f"Passed endpoints: `{summary['public_endpoint_passed_count']}/{summary['public_endpoint_count']}`",
        "",
        "| Endpoint | HTTP | Status | Failed checks |",
        "|---|---:|---|---|",
    ]
    for endpoint in audit["public_canary"]["endpoints"]:
        failed = ", ".join(endpoint["failed_checks"]) or "none"
        lines.append(
            f"| `{endpoint['endpoint_id']}` | `{endpoint['observed_status_code']}` | "
            f"`{endpoint['status']}` | {failed} |"
        )

    lines.extend(
        [
            "",
            "## Isolated Release Stage",
            "",
            f"- Hygiene: `{audit['release_scope_hygiene']['status']}`",
            f"- Hash verified: `{audit['release_scope_hygiene']['hash_verified_path_count']}/"
            f"{audit['release_scope_hygiene']['staged_path_count']}`",
            f"- Prohibited paths: `{audit['release_scope_hygiene']['prohibited_staged_path_count']}`",
            f"- Plan binding matches: `{str(audit['release_scope_hygiene']['plan_binding_matches']).lower()}`",
            "- The broad repository index is separately blocked and is not a release source.",
            "",
            "## Bounded Release Candidates",
            "",
            "These candidates still require every global gate and a fresh action-time HumanUnlock.",
            "",
        ]
    )
    for item in audit["release_plan"]["bounded_candidates_after_global_gates"]:
        lines.append(
            f"- `{item['id']}`: `{item['claim_state']}`; action `{item['planned_action']}`"
        )

    lines.extend(["", "## Deferred Full-Plan Artifacts", ""])
    for item in audit["release_plan"]["deferred_full_plan_artifacts"]:
        lines.append(f"- `{item['id']}`: {', '.join(item['blockers'])}")

    gateway = audit["gateway_repair_candidate"]
    lines.extend(
        [
            "",
            "## Gateway Repair",
            "",
            f"- State: `{gateway['status']}`",
            f"- Module SHA-256: `{gateway['module_sha256']}`",
            f"- Repair script SHA-256: `{gateway['repair_script_sha256']}`",
            f"- Apply allowed by this audit: `{str(gateway['apply_allowed']).lower()}`",
            f"- Boundary: {gateway['boundary']}",
            "- Required exact one-time approval text:",
            "",
            f"  `{gateway['required_exact_approval_text']}`",
            "",
            f"- HumanUnlock: {gateway['human_unlock_instruction']}",
            "",
            "## Deployment Transport",
            "",
            "| Script | Strict host verification | Disabled verification found | HumanUnlock | Blockers |",
            "|---|---|---|---|---|",
        ]
    )
    for row in audit["deployment_transport_audit"]:
        lines.append(
            f"| `{row['path']}` | `{str(row['strict_host_key_checking_yes_detected']).lower()}` | "
            f"`{str(row['strict_host_key_checking_no_detected']).lower()}` | "
            f"`{str(row['human_unlock_gate_detected']).lower()}` | {', '.join(row['blockers']) or 'none'} |"
        )

    lines.extend(
        [
            "",
            "## Safest Next Action",
            "",
            audit["safest_next_action"],
            "",
            "## Receipt",
            "",
            f"Audit SHA-256: `{audit['audit_sha256']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_audit_outputs(
    audit: dict[str, Any],
    *,
    output_json: Path,
    output_markdown: Path,
    latest_json: Path | None = None,
    latest_markdown: Path | None = None,
) -> None:
    serialized = json.dumps(audit, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    markdown = render_markdown(audit)
    write_text_atomic(output_json, serialized)
    write_text_atomic(output_markdown, markdown)
    if latest_json is not None:
        write_text_atomic(latest_json, serialized)
    if latest_markdown is not None:
        write_text_atomic(latest_markdown, markdown)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only VPS and public-release security audit."
    )
    parser.add_argument("--as-of-utc")
    parser.add_argument("--output-json", type=Path, default=OUT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=OUT_MD)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    audit = build_audit(as_of_utc=args.as_of_utc)
    write_audit_outputs(
        audit,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
        latest_json=OUT_LATEST_JSON if args.output_json == OUT_JSON else None,
        latest_markdown=OUT_LATEST_MD if args.output_markdown == OUT_MD else None,
    )
    print(f"STATUS={audit['summary']['status']}")
    print(
        "PUBLIC_ENDPOINTS="
        f"{audit['summary']['public_endpoint_passed_count']}/"
        f"{audit['summary']['public_endpoint_count']}"
    )
    print(f"CANDIDATE_ARTIFACTS={audit['summary']['candidate_artifact_count']}")
    print(f"AUDIT_SHA256={audit['audit_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
