"""Build an isolated local stage bundle from the public-release sync plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = ROOT / "out" / "ops" / "PUBLIC_RELEASE_SYNC_PLAN_2026-07-18.json"
DEPLOY_STAGE = ROOT / ".deploy_stage"

PLAN_SCHEMA = "lumencore.public_release_sync_plan.v1"
STAGE_SCHEMA = "lumencore.public_release_stage_bundle.v1"
HUMAN_GATE = "HUMAN_UNLOCK_REQUIRED"
ALLOWED_ACTIONS = {"PLAN_NEW_LOCAL_STAGE_COPY", "NOOP_EXACT_MATCH"}
ALLOWED_TARGET_ROOTS = {
    Path("dashboard/evidence"),
    Path("dashboard/data"),
}


class StageError(ValueError):
    """Raised when an isolated release stage cannot be built safely."""


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StageError(f"Unreadable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise StageError(f"Expected a JSON object: {path}")
    return payload


def relative_file(root: Path, value: Any, label: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value:
        raise StageError(f"{label} is missing")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise StageError(f"{label} is not a safe relative path: {value}")
    try:
        resolved = (root / relative).resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise StageError(f"{label} is missing or outside the repository: {value}") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise StageError(f"{label} is not a regular repository file: {value}")
    return relative.as_posix(), resolved


def safe_target(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise StageError("target_path is missing")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise StageError(f"target_path is unsafe: {value}")
    normalized = Path(relative.as_posix())
    if not any(normalized == root or root in normalized.parents for root in ALLOWED_TARGET_ROOTS):
        raise StageError(f"target_path is outside the release surface: {value}")
    return normalized.as_posix()


def verify_plan_hash(plan: dict[str, Any]) -> str:
    declared = str(plan.get("plan_sha256", "")).lower()
    unsigned = dict(plan)
    unsigned.pop("plan_sha256", None)
    observed = stable_sha256(unsigned)
    if not declared or observed != declared:
        raise StageError("Release plan SHA-256 is invalid")
    return declared


def stage_root_for(plan_sha256: str, *, root: Path, deploy_stage: Path) -> Path:
    root_resolved = root.resolve(strict=True)
    stage_base = deploy_stage.resolve(strict=False)
    expected_base = (root_resolved / ".deploy_stage").resolve(strict=False)
    if stage_base != expected_base:
        raise StageError("Local stage root must be the repository .deploy_stage directory")
    destination = stage_base / f"public_reviewer_release_{plan_sha256[:16]}"
    try:
        destination.resolve(strict=False).relative_to(expected_base)
    except ValueError as exc:
        raise StageError("Computed stage destination escaped .deploy_stage") from exc
    return destination


def build_stage_contract(
    plan_path: Path = DEFAULT_PLAN,
    *,
    root: Path = ROOT,
    deploy_stage: Path = DEPLOY_STAGE,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    plan = read_json(plan_path)
    plan_sha256 = verify_plan_hash(plan)
    summary = plan.get("summary", {})
    network_actions = plan.get("network_actions", {})
    if (
        plan.get("schema") != PLAN_SCHEMA
        or plan.get("mode") != "DRY_RUN_ONLY"
        or plan.get("human_gate") != HUMAN_GATE
        or summary.get("plan_state") != "DRY_RUN_READY_HUMAN_UNLOCK_REQUIRED"
        or summary.get("blocked_count") != 0
        or summary.get("local_copy_performed") is not False
        or summary.get("network_action_performed") is not False
        or summary.get("public_release_completed") is not False
        or not network_actions
        or set(network_actions.values()) != {HUMAN_GATE}
    ):
        raise StageError("Release plan is not a fail-closed dry-run-ready contract")

    stage_root = stage_root_for(plan_sha256, root=root, deploy_stage=deploy_stage)
    files: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    for item in plan.get("items", []):
        if not isinstance(item, dict):
            raise StageError("Release plan contains an invalid item")
        item_id = str(item.get("id", ""))
        if (
            not item_id
            or item.get("blockers") != []
            or item.get("planned_action") not in ALLOWED_ACTIONS
            or item.get("copy_performed") is not False
            or item.get("network_action_performed") is not False
        ):
            raise StageError(f"Release item is not stageable: {item_id or '<missing>'}")
        source_rel, source = relative_file(root, item.get("source_path"), "source_path")
        expected_sha = str(item.get("source_sha256", "")).lower()
        observed_sha = sha256_file(source)
        if not expected_sha or observed_sha != expected_sha:
            raise StageError(f"Release source drifted: {source_rel}")
        target_rel = safe_target(item.get("target_path"))
        if target_rel in seen_targets:
            raise StageError(f"Duplicate release target: {target_rel}")
        seen_targets.add(target_rel)
        public_verification = item.get("public_url_verification", {})
        if (
            public_verification.get("network_request_performed") is not False
            or public_verification.get("state")
            != "PENDING_HUMAN_UNLOCK_AND_PUBLICATION"
            or public_verification.get("expected_sha256") != expected_sha
        ):
            raise StageError(f"Public verification state is unsafe: {item_id}")
        files.append(
            {
                "id": item_id,
                "source_path": source_rel,
                "source_sha256": expected_sha,
                "bytes": source.stat().st_size,
                "staged_relative_path": target_rel,
                "intended_public_target_path": target_rel,
                "public_url": public_verification.get("url"),
                "mime_type": item.get("mime_type"),
            }
        )

    if len(files) != summary.get("item_count"):
        raise StageError("Release item count does not match the plan summary")

    try:
        plan_relative = plan_path.resolve(strict=True).relative_to(root).as_posix()
        stage_relative = stage_root.relative_to(root).as_posix()
    except ValueError as exc:
        raise StageError("Plan or stage path is outside the repository") from exc

    contract: dict[str, Any] = {
        "schema": STAGE_SCHEMA,
        "stage_state": "CHECK_READY_NOT_STAGED",
        "plan_path": plan_relative,
        "plan_sha256": plan_sha256,
        "stage_root": stage_relative,
        "files": files,
        "summary": {
            "item_count": len(files),
            "files_staged_locally": False,
            "public_root_copy_performed": False,
            "network_action_performed": False,
            "publication_performed": False,
            "stage_ready": True,
        },
        "authority": {
            "human_unlock_required_for_vps_or_publication": True,
            "external_action_authorized_by_stage": False,
            "credentials_required_for_local_stage": False,
        },
        "boundary": (
            "This bundle is an isolated local copy under .deploy_stage. It does not "
            "write public roots, contact the VPS, publish, deploy, or authorize release."
        ),
    }
    contract["manifest_sha256"] = stable_sha256(contract)
    return contract


def verify_manifest_hash(manifest: dict[str, Any]) -> None:
    declared = str(manifest.get("manifest_sha256", "")).lower()
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    if not declared or stable_sha256(unsigned) != declared:
        raise StageError("Stage manifest SHA-256 is invalid")


def verify_existing_stage(stage_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    manifest_path = stage_root / "manifest.json"
    existing = read_json(manifest_path)
    verify_manifest_hash(existing)
    if (
        existing.get("schema") != STAGE_SCHEMA
        or existing.get("plan_sha256") != contract["plan_sha256"]
        or existing.get("stage_state") != "LOCAL_STAGE_READY"
    ):
        raise StageError("Existing stage does not match the requested release plan")
    for row in existing.get("files", []):
        relative = safe_target(row.get("staged_relative_path"))
        staged = stage_root / relative
        if (
            not staged.is_file()
            or staged.is_symlink()
            or sha256_file(staged) != row.get("source_sha256")
        ):
            raise StageError(f"Existing staged file failed verification: {relative}")
    return existing


def stage_bundle(contract: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    verify_manifest_hash(contract)
    root = root.resolve(strict=True)
    stage_root = root / contract["stage_root"]
    expected_base = (root / ".deploy_stage").resolve(strict=False)
    try:
        stage_root.resolve(strict=False).relative_to(expected_base)
    except ValueError as exc:
        raise StageError("Stage destination is outside .deploy_stage") from exc
    if stage_root.exists():
        return verify_existing_stage(stage_root, contract)

    temporary = stage_root.with_name(f".{stage_root.name}.tmp")
    if temporary.exists():
        raise StageError(f"Temporary stage already exists: {temporary}")
    temporary.mkdir(parents=True)
    try:
        for row in contract["files"]:
            source = root / row["source_path"]
            destination = temporary / row["staged_relative_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if sha256_file(destination) != row["source_sha256"]:
                raise StageError(
                    f"Staged copy failed SHA-256 verification: {row['staged_relative_path']}"
                )

        manifest = dict(contract)
        manifest["stage_state"] = "LOCAL_STAGE_READY"
        manifest["summary"] = {
            **contract["summary"],
            "files_staged_locally": True,
        }
        manifest.pop("manifest_sha256", None)
        manifest["manifest_sha256"] = stable_sha256(manifest)
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        temporary.rename(stage_root)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check or build an isolated local public-reviewer release stage."
    )
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.stage and args.check:
        parser.error("--stage and --check are mutually exclusive")
    return args


def main() -> int:
    args = parse_args()
    root = args.root.resolve(strict=True)
    deploy_stage = root / ".deploy_stage"
    contract = build_stage_contract(
        args.plan,
        root=root,
        deploy_stage=deploy_stage,
    )
    if args.stage:
        manifest = stage_bundle(contract, root=root)
        print(f"Local stage ready: {root / manifest['stage_root']}")
        print(f"Manifest SHA-256: {manifest['manifest_sha256']}")
    else:
        print("Local stage check passed; no files copied.")
        print(f"Planned stage root: {root / contract['stage_root']}")
        print(f"Plan SHA-256: {contract['plan_sha256']}")
    print("HumanUnlock remains required for VPS or publication action.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
