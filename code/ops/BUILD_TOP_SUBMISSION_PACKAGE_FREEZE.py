from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GRANTS = ROOT / "grant_submissions"
OUT = ROOT / "out" / "ops"

READINESS_JSON = OUT / "grant_submission_readiness_audit_latest.json"
OUT_JSON = OUT / "top_submission_package_freeze_latest.json"
OUT_MD = GRANTS / "TOP_SUBMISSION_PACKAGE_FREEZE_2026-06-20.md"

PACKAGE_ORDER = ["DICE", "HarborSentinel"]

CLAIM_BOUNDARY = (
    "This freeze hashes local package artifacts only. It does not approve upload, "
    "certify eligibility or compliance, validate cost, prove partner authority, "
    "or replace portal preview and fresh action-time approval."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def role_for_path(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".docx") and ("draft" in lower or "working" in lower):
        return "upload_candidate_docx"
    if lower.endswith(".pdf") and "render_qa" in lower:
        return "render_preview_pdf"
    if "cost" in lower:
        return "cost_boundary"
    if "live_breadth_provenance_annex" in lower:
        return "provenance_annex"
    if "live_breadth_replay" in lower:
        return "frozen_live_replay_evidence"
    if "evidence_synthesis" in lower:
        return "evidence_synthesis"
    if "review_burden" in lower:
        return "review_burden_evidence"
    if "heilmeier" in lower or "reviewer" in lower:
        return "reviewer_matrix"
    if "reference" in lower:
        return "reference_matrix"
    if "ais" in lower or "public" in lower or "data_source" in lower:
        return "representative_data_evidence"
    if "finalization" in lower or "source_qa" in lower:
        return "package_qa"
    if lower.endswith(".pdf"):
        return "official_or_render_pdf"
    if lower.endswith(".docx"):
        return "docx_artifact"
    return "supporting_artifact"


def package_by_name(readiness: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packages = readiness.get("packages", [])
    if not isinstance(packages, list):
        return {}
    return {
        str(row.get("name")): row
        for row in packages
        if isinstance(row, dict) and row.get("name")
    }


def freeze_artifact(row: dict[str, Any]) -> dict[str, Any]:
    path_text = str(row.get("path", ""))
    path = ROOT / path_text
    exists = path.exists()
    is_file = exists and path.is_file()
    return {
        "path": path_text.replace("\\", "/"),
        "role": role_for_path(path_text),
        "exists": exists,
        "bytes": path.stat().st_size if is_file else None,
        "sha256": sha256_file(path) if is_file else None,
    }


def freeze_package(pkg: dict[str, Any]) -> dict[str, Any]:
    artifacts = [
        freeze_artifact(row)
        for row in pkg.get("required_artifacts", [])
        if isinstance(row, dict)
    ]
    local_blockers = [str(item) for item in pkg.get("local_blockers", []) or []]
    portal_blockers = [str(item) for item in pkg.get("portal_user_blockers", []) or []]
    upload_candidates = [
        row for row in artifacts if row["role"] in {"upload_candidate_docx", "render_preview_pdf"}
    ]
    missing = [row["path"] for row in artifacts if not row["exists"]]
    return {
        "name": pkg.get("name", ""),
        "portal": pkg.get("portal", ""),
        "readiness": pkg.get("readiness", "UNKNOWN"),
        "local_ready": not local_blockers and not missing,
        "ready_for_portal_upload": False,
        "ready_for_portal_upload_reason": (
            "Portal/user gates remain open."
            if portal_blockers
            else "Fresh action-time approval is still required even when portal gates appear clear."
        ),
        "artifact_count": len(artifacts),
        "missing_artifacts": missing,
        "upload_candidates": upload_candidates,
        "artifacts": artifacts,
        "portal_user_blocker_count": len(portal_blockers),
        "portal_user_blockers": portal_blockers,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def build_freeze(readiness: dict[str, Any] | None = None) -> dict[str, Any]:
    readiness = readiness or read_json(READINESS_JSON)
    packages = package_by_name(readiness)
    frozen = [
        freeze_package(packages[name])
        for name in PACKAGE_ORDER
        if name in packages
    ]
    all_artifacts = [
        artifact
        for package in frozen
        for artifact in package["artifacts"]
    ]
    material = {
        "schema": "top_submission_package_freeze_material_v1",
        "packages": [
            {
                "name": package["name"],
                "artifacts": [
                    {
                        "path": artifact["path"],
                        "bytes": artifact["bytes"],
                        "sha256": artifact["sha256"],
                    }
                    for artifact in package["artifacts"]
                ],
            }
            for package in frozen
        ],
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "generated_utc": now_utc(),
        "schema": "top_submission_package_freeze_v1",
        "readiness_source": rel(READINESS_JSON),
        "source_posture": readiness.get("posture", "UNKNOWN"),
        "source_summary": readiness.get("summary", {}),
        "claim_boundary": CLAIM_BOUNDARY,
        "package_count": len(frozen),
        "artifact_count": len(all_artifacts),
        "all_required_artifacts_present": all(row["exists"] for row in all_artifacts),
        "ready_for_portal_upload": False,
        "freeze_signature_sha256": hashlib.sha256(canonical).hexdigest(),
        "packages": frozen,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Top Submission Package Freeze",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        f"Source posture: `{payload.get('source_posture', 'UNKNOWN')}`",
        f"Freeze signature SHA-256: `{payload['freeze_signature_sha256']}`",
        "",
        "## Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Packages frozen: {payload['package_count']}",
        f"- Artifacts hashed: {payload['artifact_count']}",
        f"- All required artifacts present: {payload['all_required_artifacts_present']}",
        f"- Ready for portal upload: {payload['ready_for_portal_upload']}",
        "",
        "## Packages",
        "",
    ]
    for package in payload["packages"]:
        lines.extend(
            [
                f"### {package['name']} ({package['portal']})",
                "",
                f"- Readiness: `{package['readiness']}`",
                f"- Local ready: {package['local_ready']}",
                f"- Ready for portal upload: {package['ready_for_portal_upload']}",
                f"- Reason: {package['ready_for_portal_upload_reason']}",
                f"- Portal/user blockers: {package['portal_user_blocker_count']}",
                "",
                "#### Upload Candidates",
                "",
                "| Role | Artifact | Bytes | SHA-256 |",
                "|---|---|---:|---|",
            ]
        )
        for artifact in package["upload_candidates"]:
            lines.append(
                f"| {artifact['role']} | `{artifact['path']}` | {artifact['bytes']} | `{artifact['sha256']}` |"
            )
        lines.extend(
            [
                "",
                "#### Full Artifact Hashes",
                "",
                "| Role | Artifact | Bytes | SHA-256 |",
                "|---|---|---:|---|",
            ]
        )
        for artifact in package["artifacts"]:
            sha = artifact["sha256"] or "missing"
            bytes_text = artifact["bytes"] if artifact["bytes"] is not None else "missing"
            lines.append(
                f"| {artifact['role']} | `{artifact['path']}` | {bytes_text} | `{sha}` |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    payload = build_freeze()
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "posture": payload["source_posture"],
                "packages": payload["package_count"],
                "artifacts": payload["artifact_count"],
                "all_required_artifacts_present": payload["all_required_artifacts_present"],
                "ready_for_portal_upload": payload["ready_for_portal_upload"],
                "signature": payload["freeze_signature_sha256"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
