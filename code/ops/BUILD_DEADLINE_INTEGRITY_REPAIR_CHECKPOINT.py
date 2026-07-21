from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
RECEIPT = SPRINT_DIR / "DEADLINE_INTEGRITY_REPAIR_CHECKPOINT_2026-07-21.json"
SIDECAR = RECEIPT.with_suffix(RECEIPT.suffix + ".sha256")
VAULT_ROOT = Path("E:/LumaProofVault")
DESTINATION_ROOT = VAULT_ROOT / "SUBMISSIONS" / "DEADLINE_INTEGRITY_REPAIR_20260721"

SOURCES = (
    "code/ops/BUILD_DEADLINE_INTEGRITY_REPAIR_CHECKPOINT.py",
    "code/ops/BUILD_HUMAN_ACTION_DOCKET.py",
    "code/ops/BUILD_LIVE_FUNDING_PORTAL_HANDOFF.py",
    "code/ops/BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py",
    "code/ops/BUILD_SUBMISSION_AUTHORITY_MATRIX.py",
    "dashboard/data/human_action_docket.json",
    "dashboard/data/submission_authority_matrix.json",
    "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
    "out/ops/human_action_docket_latest.json",
    "out/ops/submission_authority_matrix_latest.json",
    "tests/test_agency_account_activation_docket.py",
    "tests/test_deadline_integrity_repair_checkpoint.py",
    "tests/test_epri_open_power_ai_mou_response.py",
    "tests/test_erdc_sdc_phase2_rom_gate.py",
    "tests/test_federal_submission_protocol_packet.py",
    "tests/test_launchtn_3686_pitch_application.py",
    "tests/test_live_funding_portal_handoff.py",
    "tests/test_nashville_ec_live_deadline_receipt.py",
    "tests/test_near_deadline_submission_command_board.py",
    "tests/test_nsf_project_pitch_routing_control.py",
    "tests/test_openai_build_week_readiness_packet.py",
    "tests/test_prepare_patent_center_private_capture.py",
    "tests/test_submission_authority_matrix.py",
    "tests/test_traction_opportunity_intake_ledger.py",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256_bytes(encoded)


def run_git(*args: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=text,
    )
    return completed.stdout.strip() if text else completed.stdout


def source_path(relative_path: str) -> Path:
    relative = Path(relative_path)
    normalized = relative_path.replace("\\", "/").lower()
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or "/private/" in f"/{normalized}/"
        or ".private." in normalized
    ):
        raise ValueError(f"Unsafe checkpoint source: {relative_path}")
    source = (ROOT / relative).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
        raise ValueError(f"Missing or out-of-root checkpoint source: {relative_path}")
    return source


def committed_blob(commit: str, relative_path: str) -> bytes:
    return run_git("show", f"{commit}:{relative_path}", text=False)


def destination_path(relative_path: str) -> Path:
    destination = (DESTINATION_ROOT / relative_path).resolve()
    if not destination.is_relative_to(DESTINATION_ROOT.resolve()):
        raise ValueError(f"Unsafe checkpoint destination: {relative_path}")
    return destination


def build_receipt(created_utc: str | None = None) -> dict[str, Any]:
    tracked_status = str(run_git("status", "--porcelain", "--untracked-files=no"))
    if tracked_status:
        raise ValueError("Tracked worktree must be clean before checkpointing")
    if not VAULT_ROOT.is_dir():
        raise ValueError(f"E-drive proof vault is unavailable: {VAULT_ROOT}")

    source_commit = str(run_git("rev-parse", "HEAD"))
    source_branch = str(run_git("branch", "--show-current"))
    DESTINATION_ROOT.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, Any]] = []
    for relative_path in SOURCES:
        source = source_path(relative_path)
        worktree_bytes = source.read_bytes()
        commit_bytes = committed_blob(source_commit, relative_path)
        if worktree_bytes != commit_bytes:
            raise ValueError(f"Worktree bytes differ from source commit: {relative_path}")

        destination = destination_path(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        source_hash = sha256_bytes(worktree_bytes)
        destination_hash = sha256_file(destination)
        if source_hash != destination_hash or len(worktree_bytes) != destination.stat().st_size:
            raise ValueError(f"Checkpoint mirror verification failed: {relative_path}")
        artifacts.append(
            {
                "source": relative_path,
                "destination": destination.as_posix(),
                "bytes": len(worktree_bytes),
                "sha256": source_hash,
                "source_commit_blob_match": True,
                "copy_bytes": destination.stat().st_size,
                "copy_sha256": destination_hash,
                "copy_sha256_matched": True,
            }
        )

    payload: dict[str, Any] = {
        "schema": "lumencore.deadline_integrity_repair_checkpoint.v1",
        "created_utc": created_utc or now_utc(),
        "source_commit": source_commit,
        "source_branch": source_branch,
        "source_worktree_tracked_clean": True,
        "destination_root": DESTINATION_ROOT.as_posix(),
        "artifact_count": len(artifacts),
        "all_source_bytes_match_commit": True,
        "all_sha256_matched_after_copy": True,
        "relative_paths_preserved": True,
        "private_files_mirrored": False,
        "browser_navigation_performed": False,
        "external_send_performed": False,
        "portal_submission_performed": False,
        "certification_or_terms_accepted": False,
        "artifacts": artifacts,
        "receipt_copy_destination": (
            DESTINATION_ROOT / RECEIPT.relative_to(ROOT)
        ).as_posix(),
        "sidecar_copy_destination": (
            DESTINATION_ROOT / SIDECAR.relative_to(ROOT)
        ).as_posix(),
        "claim_boundary": (
            "This receipt proves only that the listed public deadline-routing code, tests, and "
            "generated control surfaces matched the recorded Git commit and were copied to the "
            "stated E-drive directory with matching SHA-256 hashes. It does not prove email "
            "transmission, portal submission, eligibility, certification, award, endorsement, "
            "external validation, technical performance, funding, or value. Final external and "
            "legal actions remain human-controlled."
        ),
    }
    payload["receipt_payload_sha256"] = stable_hash(payload)
    return payload


def write_and_mirror_receipt(payload: dict[str, Any]) -> str:
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    receipt_file_sha256 = sha256_file(RECEIPT)
    SIDECAR.write_text(f"{receipt_file_sha256}  {RECEIPT.name}\n", encoding="ascii")

    receipt_copy = Path(payload["receipt_copy_destination"])
    sidecar_copy = Path(payload["sidecar_copy_destination"])
    receipt_copy.parent.mkdir(parents=True, exist_ok=True)
    sidecar_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RECEIPT, receipt_copy)
    shutil.copy2(SIDECAR, sidecar_copy)
    if sha256_file(receipt_copy) != receipt_file_sha256:
        raise ValueError("Checkpoint receipt copy hash mismatch")
    if sha256_file(sidecar_copy) != sha256_file(SIDECAR):
        raise ValueError("Checkpoint sidecar copy hash mismatch")
    return receipt_file_sha256


def main() -> int:
    payload = build_receipt()
    receipt_file_sha256 = write_and_mirror_receipt(payload)
    print(
        json.dumps(
            {
                "status": "DEADLINE_INTEGRITY_REPAIR_CHECKPOINT_VERIFIED",
                "source_commit": payload["source_commit"],
                "artifact_count": payload["artifact_count"],
                "receipt_payload_sha256": payload["receipt_payload_sha256"],
                "receipt_file_sha256": receipt_file_sha256,
                "destination_root": payload["destination_root"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
