"""Build the current, fail-closed publication approval packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

FRONT_DOOR_JSON = OUT_OPS / "current_reviewer_front_door_latest.json"
PUBLIC_ARTIFACT_MANIFEST = (
    DOCS / "receipts" / "CURRENT_REVIEWER_PUBLIC_ARTIFACT_MANIFEST_2026-07-29.json"
)
PUBLIC_RELEASE_POLICY = ROOT / "config" / "public_release_sync_policy_v1.json"
WHITEPAPER_MANIFEST = OUT_OPS / "source_native_research_whitepaper_manifest_latest.json"
VPS_SECURITY_AUDIT = OUT_OPS / "vps_public_release_security_audit_20260802.json"

OUT_JSON = OUT_OPS / "publication_approval_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "publication_approval_packet.json"
OUT_MD = DOCS / "PUBLICATION_APPROVAL_PACKET_CURRENT.md"

SCHEMA = "lumencore.publication_approval_packet.v4"
STATUS = "CURRENT_ARTIFACT_SET_HASH_BOUND_RELEASE_BLOCKED"
PUBLIC_REPO_URL = "https://github.com/robertashworth1986-debug/lumen-core-public"

RELEASE_ARTIFACTS = (
    {
        "artifact_id": "current_capability_statement",
        "release_item_id": "federal_capability_statement_pdf",
        "governance_id": "capability_statement_governance",
    },
    {
        "artifact_id": "current_evidence_to_pilot_deck_pdf",
        "release_item_id": "current_evidence_to_pilot_deck_pdf",
        "governance_id": "pitch_deck_governance",
    },
    {
        "artifact_id": "current_source_native_whitepaper",
        "release_item_id": "source_native_benchmark_whitepaper_pdf",
        "governance_id": "whitepaper_manifest",
    },
)


class PublicationPacketError(ValueError):
    """Raised when the current publication chain cannot be reconciled."""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationPacketError(f"Unreadable JSON: {rel(path)}") from exc
    if not isinstance(payload, dict):
        raise PublicationPacketError(f"Expected JSON object: {rel(path)}")
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def canonical_sha256(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().lower()


def serialized(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def safe_file(relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise PublicationPacketError("Artifact path is missing")
    path = (ROOT / relative).resolve(strict=True)
    try:
        path.relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise PublicationPacketError(f"Artifact is outside the repository: {relative}") from exc
    if not path.is_file():
        raise PublicationPacketError(f"Artifact is not a file: {relative}")
    return path


def unique_row(rows: Any, key: str, value: str, label: str) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise PublicationPacketError(f"Expected a list of {label} records")
    matches = [
        row
        for row in rows if isinstance(row, dict)
        and str(row.get(key)) == value
    ]
    if len(matches) != 1:
        raise PublicationPacketError(f"Expected one {label}: {value}")
    return matches[0]


def validate_front_door(front_door: dict[str, Any]) -> None:
    if front_door.get("schema") != "lumencore.current_reviewer_front_door.v1":
        raise PublicationPacketError("Current reviewer front door has the wrong schema")
    if front_door.get("status") != "CURRENT_REVIEWER_FRONT_DOOR_READY_HUMAN_RELEASE_REQUIRED":
        raise PublicationPacketError("Current reviewer front door is not release-review ready")
    expected = str(front_door.get("front_door_sha256", "")).lower()
    observed = canonical_sha256(
        {key: value for key, value in front_door.items() if key != "front_door_sha256"}
    )
    if expected != observed:
        raise PublicationPacketError("Current reviewer front-door payload hash is stale")


def validate_public_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != "lumencore.current_reviewer_public_artifact_manifest.v1":
        raise PublicationPacketError("Public artifact manifest has the wrong schema")
    expected = str(manifest.get("manifest_sha256", "")).lower()
    observed = canonical_sha256(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    )
    if expected != observed:
        raise PublicationPacketError("Public artifact manifest payload hash is stale")
    if manifest.get("external_release_authorized") is not False:
        raise PublicationPacketError("Public artifact manifest must remain fail closed")


def validate_release_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema") != "lumencore.public_release_sync_policy.v1":
        raise PublicationPacketError("Public release policy has the wrong schema")
    if policy.get("status") != "frozen" or policy.get("mode") != "DRY_RUN_ONLY":
        raise PublicationPacketError("Public release policy is not frozen and dry-run only")


def build_release_artifacts(
    front_door: dict[str, Any],
    policy: dict[str, Any],
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    front_artifacts = front_door.get("artifacts", [])
    bindings = front_door.get("public_release_bindings", {})
    allowlist = policy.get("allowlist", [])
    manifest_artifacts = manifest.get("artifacts", [])
    manifest_file_sha = sha256_file(PUBLIC_ARTIFACT_MANIFEST)
    release_rows: list[dict[str, Any]] = []

    for spec in RELEASE_ARTIFACTS:
        artifact_id = spec["artifact_id"]
        release_item_id = spec["release_item_id"]
        governance_id = spec["governance_id"]

        artifact = unique_row(front_artifacts, "id", artifact_id, "front-door artifact")
        release_item = unique_row(allowlist, "id", release_item_id, "release-policy item")
        manifest_row = unique_row(
            manifest_artifacts,
            "id",
            artifact_id,
            "public-manifest artifact",
        )
        governance = unique_row(
            front_artifacts,
            "id",
            governance_id,
            "governance artifact",
        )
        binding = bindings.get(artifact_id)
        if not isinstance(binding, dict):
            raise PublicationPacketError(f"Missing public-release binding: {artifact_id}")

        source_path = str(artifact.get("path", ""))
        source_file = safe_file(source_path)
        observed_sha = sha256_file(source_file)
        expected_sha = str(artifact.get("sha256", "")).lower()
        if observed_sha != expected_sha:
            raise PublicationPacketError(f"Current artifact hash is stale: {artifact_id}")
        if int(artifact.get("bytes", -1)) != source_file.stat().st_size:
            raise PublicationPacketError(f"Current artifact byte count is stale: {artifact_id}")

        policy_sha = str(release_item.get("expected_source_sha256", "")).lower()
        if release_item.get("source_path") != source_path or policy_sha != observed_sha:
            raise PublicationPacketError(f"Release-policy source binding is stale: {artifact_id}")
        if binding.get("release_item_id") != release_item_id:
            raise PublicationPacketError(f"Front-door release item is stale: {artifact_id}")
        if binding.get("immutable_target_path") != release_item.get("target_path"):
            raise PublicationPacketError(f"Immutable target binding is stale: {artifact_id}")
        if binding.get("public_url") != release_item.get("public_url"):
            raise PublicationPacketError(f"Public URL binding is stale: {artifact_id}")

        receipt_ref = release_item.get("artifact_receipt_ref")
        if not isinstance(receipt_ref, dict):
            raise PublicationPacketError(f"Artifact receipt is missing: {artifact_id}")
        if receipt_ref.get("path") != rel(PUBLIC_ARTIFACT_MANIFEST):
            raise PublicationPacketError(f"Artifact receipt path is stale: {artifact_id}")
        if str(receipt_ref.get("expected_sha256", "")).lower() != manifest_file_sha:
            raise PublicationPacketError(f"Artifact receipt file hash is stale: {artifact_id}")

        for key in ("path", "bytes", "sha256", "release_item_id"):
            left = str(manifest_row.get(key, "")).lower()
            right = str(artifact.get(key, "")).lower()
            if key == "release_item_id":
                right = release_item_id.lower()
            if left != right:
                raise PublicationPacketError(
                    f"Public artifact manifest binding is stale for {artifact_id}: {key}"
                )

        release_rows.append(
            {
                "artifact_id": artifact_id,
                "release_item_id": release_item_id,
                "role": artifact.get("role"),
                "source_path": source_path,
                "source_bytes": source_file.stat().st_size,
                "source_sha256": observed_sha,
                "mime_type": release_item.get("mime_type"),
                "claim_state": release_item.get("claim_state"),
                "claim_boundary": release_item.get("claim_boundary"),
                "immutable_target_path": binding.get("immutable_target_path"),
                "public_url": binding.get("public_url"),
                "publication_state": binding.get("publication_state"),
                "binding_state": "HASH_MATCHED_CURRENT",
                "governance": {
                    "id": governance_id,
                    "path": governance.get("path"),
                    "sha256": str(governance.get("sha256", "")).lower(),
                    "status": governance.get("status"),
                },
                "external_release_authorized": False,
            }
        )
    return release_rows


def build_public_copy(snapshot: dict[str, Any], panel: dict[str, Any]) -> dict[str, Any]:
    registered = int(snapshot.get("registered_family_count", 0) or 0)
    implemented = int(snapshot.get("implementation_present_count", 0) or 0)
    comparisons = int(snapshot.get("executed_comparison_count", 0) or 0)
    primary_positive = int(snapshot.get("global_holm_positive_count", 0) or 0)
    panel_positive = int(panel.get("exploratory_global_holm_positive_count", 0) or 0)
    promotions = int(snapshot.get("promotion_gate_pass_count", 0) or 0)
    full_baseline_winners = int(
        panel.get("candidate_beats_every_baseline_on_mean_count", 0) or 0
    )

    site_summary = (
        "LumenCore's current reviewer packet documents software architecture, evidence "
        "custody, source-native benchmark methods, negative results, and a frozen "
        "prospective protocol. It is a review package, not a claim of external validation, "
        "model superiority, field performance, trading alpha, realized savings, an award, "
        "or a contract."
    )
    linkedin_post = (
        "LumenCore's current evidence packet is ready for bounded technical review. "
        f"The registry contains {registered} candidate families, {implemented} current "
        f"implementations, and {comparisons} source-native comparisons. The primary ledger "
        f"has {primary_positive} globally corrected positive comparisons; the separate "
        f"retrospective panel has {panel_positive} narrow exploratory positive comparison, "
        f"{full_baseline_winners} complete-baseline winners, and {promotions} promotions. "
        "The prospective protocol remains sealed and awaits future observations. The packet "
        "publishes the method, limitations, negative results, and next validation gates."
    )
    reviewer_email = {
        "subject": "LumenCore current evidence-to-pilot reviewer packet",
        "body": (
            "Hello,\n\n"
            "I am sharing a hash-bound LumenCore reviewer packet containing the current "
            "capability statement, evidence-to-pilot deck, and source-native benchmark "
            "whitepaper. The materials separate implemented software and local benchmark "
            "evidence from prospective, independent, field, and economic validation.\n\n"
            "I would value review of source authority, baseline fairness, reproducibility, "
            "claim boundaries, and the smallest credible pilot or independent evaluation. "
            "No endorsement or performance conclusion is requested.\n\n"
            "Best,\nRobert Ashworth"
        ),
    }
    return {
        "site_summary": {
            "status": "DRAFT_EXACT_ARTIFACT_SET_REVIEW_REQUIRED",
            "copy": site_summary,
        },
        "linkedin_post": {
            "status": "DRAFT_EXACT_ARTIFACT_SET_REVIEW_REQUIRED",
            "copy": linkedin_post,
        },
        "reviewer_email": {
            "status": "DRAFT_EXACT_RECIPIENT_REVIEW_REQUIRED",
            **reviewer_email,
        },
    }


def build_payload(as_of_utc: str | None = None) -> dict[str, Any]:
    front_door = read_json(FRONT_DOOR_JSON)
    public_manifest = read_json(PUBLIC_ARTIFACT_MANIFEST)
    policy = read_json(PUBLIC_RELEASE_POLICY)
    whitepaper = read_json(WHITEPAPER_MANIFEST)
    security = read_json(VPS_SECURITY_AUDIT)

    validate_front_door(front_door)
    validate_public_manifest(public_manifest)
    validate_release_policy(policy)
    release_artifacts = build_release_artifacts(front_door, policy, public_manifest)

    front_whitepaper = unique_row(
        front_door.get("artifacts", []),
        "id",
        "whitepaper_manifest",
        "whitepaper governance artifact",
    )
    if sha256_file(WHITEPAPER_MANIFEST) != str(front_whitepaper.get("sha256", "")).lower():
        raise PublicationPacketError("Whitepaper manifest changed after the front-door seal")
    front_security = unique_row(
        front_door.get("artifacts", []),
        "id",
        "vps_public_release_security_audit",
        "VPS security audit artifact",
    )
    if sha256_file(VPS_SECURITY_AUDIT) != str(front_security.get("sha256", "")).lower():
        raise PublicationPacketError("VPS security audit changed after the front-door seal")

    snapshot = whitepaper.get("current_snapshot")
    panel = whitepaper.get("market_signal_panel_result")
    if not isinstance(snapshot, dict) or not isinstance(panel, dict):
        raise PublicationPacketError("Whitepaper evidence snapshot is missing")

    security_summary = security.get("summary")
    if not isinstance(security_summary, dict):
        raise PublicationPacketError("VPS security summary is missing")
    security_blockers = [str(item) for item in security.get("blockers", [])]
    blockers = sorted(
        set(
            security_blockers
            + [
                "ACTION_TIME_HUMAN_APPROVAL_REQUIRED",
                "PRIVATE_HUMAN_UNLOCK_RECEIPT_REQUIRED",
                "PUBLIC_ENDPOINT_HASH_VERIFICATION_PENDING",
            ]
        )
    )

    artifact_set_payload = [
        {
            "artifact_id": row["artifact_id"],
            "source_path": row["source_path"],
            "source_bytes": row["source_bytes"],
            "source_sha256": row["source_sha256"],
            "immutable_target_path": row["immutable_target_path"],
            "public_url": row["public_url"],
            "claim_boundary": row["claim_boundary"],
        }
        for row in release_artifacts
    ]
    artifact_set_sha = canonical_sha256(artifact_set_payload)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": as_of_utc or now_utc(),
        "status": STATUS,
        "purpose": (
            "Bind the exact current public-review artifact set, destinations, bounded copy, "
            "and unresolved release gates before any external publication."
        ),
        "publication_policy": {
            "external_release_authorized": False,
            "vps_mutation_allowed": False,
            "network_action_performed": False,
            "no_auto_posting": True,
            "no_private_grant_or_patent_material": True,
            "action_time_approval_required_for_every_external_publication": True,
            "exact_artifact_set_and_destination_binding_required": True,
        },
        "source_bindings": {
            "reviewer_front_door": {
                "path": rel(FRONT_DOOR_JSON),
                "status": front_door.get("status"),
                "binding_state": (
                    "VERIFIED_AT_PACKET_BUILD_OBSERVATION_TIME_EXCLUDED"
                ),
            },
            "public_artifact_manifest": {
                "path": rel(PUBLIC_ARTIFACT_MANIFEST),
                "file_sha256": sha256_file(PUBLIC_ARTIFACT_MANIFEST),
                "payload_sha256": str(public_manifest["manifest_sha256"]).lower(),
                "status": public_manifest.get("status"),
            },
            "public_release_policy": {
                "path": rel(PUBLIC_RELEASE_POLICY),
                "file_sha256": sha256_file(PUBLIC_RELEASE_POLICY),
                "status": policy.get("status"),
                "mode": policy.get("mode"),
            },
            "whitepaper_manifest": {
                "path": rel(WHITEPAPER_MANIFEST),
                "file_sha256": sha256_file(WHITEPAPER_MANIFEST),
                "payload_sha256": str(whitepaper.get("manifest_sha256", "")).lower(),
                "status": whitepaper.get("status"),
            },
            "vps_security_audit": {
                "path": rel(VPS_SECURITY_AUDIT),
                "file_sha256": sha256_file(VPS_SECURITY_AUDIT),
                "status": security_summary.get("status"),
            },
        },
        "evidence_snapshot": {
            "registered_family_count": snapshot.get("registered_family_count"),
            "implementation_present_count": snapshot.get("implementation_present_count"),
            "executed_comparison_count": snapshot.get("executed_comparison_count"),
            "primary_global_holm_positive_count": snapshot.get("global_holm_positive_count"),
            "panel_exploratory_global_holm_positive_count": panel.get(
                "exploratory_global_holm_positive_count"
            ),
            "panel_complete_baseline_winner_count": panel.get(
                "candidate_beats_every_baseline_on_mean_count"
            ),
            "promotion_count": snapshot.get("promotion_gate_pass_count"),
            "prospective_protocol_status": whitepaper.get("prospective_protocol", {}).get(
                "protocol_status"
            ),
            "eligible_future_observation_count": whitepaper.get(
                "prospective_protocol", {}
            ).get("eligible_future_observation_count"),
            "performance_claim_allowed": False,
        },
        "release_artifacts": release_artifacts,
        "artifact_set_sha256": artifact_set_sha,
        "human_action_gate": {
            "approval_state": "NOT_APPROVED",
            "approved_by": None,
            "approved_at_utc": None,
            "bound_artifact_set_sha256": None,
            "bound_destinations": [],
            "private_human_unlock_receipt": None,
            "single_use": True,
            "reusable_for_changed_artifacts_or_destinations": False,
        },
        "release_readiness": {
            "current_artifact_binding_count": len(release_artifacts),
            "all_artifacts_hash_matched": all(
                row["binding_state"] == "HASH_MATCHED_CURRENT"
                for row in release_artifacts
            ),
            "vps_security_status": security_summary.get("status"),
            "public_release_allowed": False,
            "vps_mutation_allowed": False,
            "blockers": blockers,
        },
        "channel_plan": [
            {
                "priority": 1,
                "channel": "lumen-core.ai",
                "action": "Publish the three immutable hash-named PDF targets only after every gate clears.",
                "approval_required": True,
            },
            {
                "priority": 2,
                "channel": "GitHub",
                "action": "Expose only the current public-safe governance and reviewer pointers on a reviewed branch.",
                "url": PUBLIC_REPO_URL,
                "approval_required": True,
            },
            {
                "priority": 3,
                "channel": "LinkedIn",
                "action": "Post bounded copy only after the three public URLs pass exact hash verification.",
                "approval_required": True,
            },
            {
                "priority": 4,
                "channel": "Reviewer email",
                "action": "Send only to an exact reviewed recipient after duplicate and disclosure checks.",
                "approval_required": True,
            },
        ],
        "public_copy_drafts": build_public_copy(snapshot, panel),
        "do_not_publish": [
            "Credentials, tokens, account screenshots, private identifiers, or meeting credentials.",
            "Patent drafts, private master-whitepaper sources, grant portal answers, budgets, or certifications.",
            "Trading profit, alpha, realized savings, customer adoption, award, contract, or valuation claims.",
            "Agency, partner, customer, evaluator, or investor endorsement without written authority.",
        ],
        "claim_boundary": whitepaper.get("boundary"),
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["packet_payload_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    readiness = payload["release_readiness"]
    snapshot = payload["evidence_snapshot"]
    lines = [
        "# LumenCore Current Publication Approval Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Status: `{payload['status']}`",
        f"Artifact-set SHA-256: `{payload['artifact_set_sha256']}`",
        "",
        "## Exact Release Set",
        "",
        "| Artifact | Source SHA-256 | Immutable target | State |",
        "|---|---|---|---|",
    ]
    for row in payload["release_artifacts"]:
        lines.append(
            f"| {row['artifact_id']} | `{row['source_sha256']}` | "
            f"`{row['immutable_target_path']}` | `{row['publication_state']}` |"
        )
    lines.extend(
        [
            "",
            "## Evidence Snapshot",
            "",
            f"- Registered families: `{snapshot['registered_family_count']}`",
            f"- Implemented families: `{snapshot['implementation_present_count']}`",
            f"- Source-native comparisons: `{snapshot['executed_comparison_count']}`",
            f"- Primary globally corrected positives: `{snapshot['primary_global_holm_positive_count']}`",
            f"- Exploratory panel globally corrected positives: `{snapshot['panel_exploratory_global_holm_positive_count']}`",
            f"- Complete-baseline winners: `{snapshot['panel_complete_baseline_winner_count']}`",
            f"- Promotions: `{snapshot['promotion_count']}`",
            f"- Prospective protocol: `{snapshot['prospective_protocol_status']}`",
            f"- Eligible future observations: `{snapshot['eligible_future_observation_count']}`",
            "",
            "## Release Blockers",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in readiness["blockers"])
    lines.extend(
        [
            "",
            "## Public Copy Drafts",
            "",
            "### Site Summary",
            "",
            payload["public_copy_drafts"]["site_summary"]["copy"],
            "",
            "### LinkedIn",
            "",
            payload["public_copy_drafts"]["linkedin_post"]["copy"],
            "",
            "### Reviewer Email",
            "",
            f"Subject: {payload['public_copy_drafts']['reviewer_email']['subject']}",
            "",
            payload["public_copy_drafts"]["reviewer_email"]["body"],
            "",
            "## Human Gate",
            "",
            "External release remains disabled. Approval must bind the exact artifact-set "
            "hash and exact destinations and must be accompanied by a fresh, private, "
            "single-use HumanUnlock receipt.",
            "",
            "## Claim Boundary",
            "",
            str(payload["claim_boundary"]),
            "",
            f"Packet SHA-256: `{payload['packet_payload_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(serialized(payload), encoding="utf-8")
    DASHBOARD_JSON.write_text(serialized(payload), encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        published = read_json(OUT_JSON)
        payload = build_payload(str(published["generated_utc"]))
        expected = {
            OUT_JSON: serialized(payload),
            DASHBOARD_JSON: serialized(payload),
            OUT_MD: render_markdown(payload),
        }
        stale = [rel(path) for path, content in expected.items() if not path.is_file() or path.read_text(encoding="utf-8") != content]
        if stale:
            raise PublicationPacketError(
                "Publication approval outputs are stale: " + ", ".join(stale)
            )
        print(json.dumps({"status": "CURRENT", "packet_payload_sha256": payload["packet_payload_sha256"]}, indent=2))
        return 0

    payload = build_payload(args.as_of_utc)
    write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "artifact_set_sha256": payload["artifact_set_sha256"],
                "packet_payload_sha256": payload["packet_payload_sha256"],
                "public_release_allowed": payload["release_readiness"][
                    "public_release_allowed"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
