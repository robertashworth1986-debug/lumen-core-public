from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "grant_submissions" / "OPENAI_BUILD_WEEK_20260721"
RECEIPT = OUT_DIR / "OPENAI_BUILD_WEEK_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
VAULT_ROOT = Path("E:/LumaProofVault")
DESTINATION_ROOT = Path("E:/LumaProofVault/OPPORTUNITIES/OPENAI_BUILD_WEEK_20260721")

SOURCES = (
    "build_week/prooflock_console/README.md",
    "build_week/prooflock_console/app.js",
    "build_week/prooflock_console/index.html",
    "build_week/prooflock_console/sample_receipt.json",
    "build_week/prooflock_console/styles.css",
    "build_week/prooflock_console/verify_receipt.py",
    "code/ops/BUILD_OPENAI_BUILD_WEEK_READINESS_PACKET.py",
    "code/ops/BUILD_OPENAI_BUILD_WEEK_E_DRIVE_SYNC_RECEIPT.py",
    "tests/test_openai_build_week_readiness_packet.py",
    "tests/test_prooflock_console.py",
    "grant_submissions/OPENAI_BUILD_WEEK_20260721/OPENAI_BUILD_WEEK_SUBMISSION_READINESS_2026-07-17.json",
    "grant_submissions/OPENAI_BUILD_WEEK_20260721/OPENAI_BUILD_WEEK_SUBMISSION_READINESS_2026-07-17.md",
    "grant_submissions/OPENAI_BUILD_WEEK_20260721/OPENAI_BUILD_WEEK_PROJECT_DESCRIPTION_DRAFT_2026-07-17.md",
    "grant_submissions/OPENAI_BUILD_WEEK_20260721/OPENAI_BUILD_WEEK_DEMO_SCRIPT_2026-07-17.md",
    "grant_submissions/OPENAI_BUILD_WEEK_20260721/OPENAI_BUILD_WEEK_REQUIREMENTS_RECEIPT_2026-07-17.json",
    "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v2_concept.json",
    "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v2_concept.png",
    "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.json",
    "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.png",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest().upper()


def source_path(relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe mirror source: {relative_path}")
    candidate = (ROOT / relative).resolve()
    if not candidate.is_relative_to(ROOT.resolve()) or not candidate.is_file():
        raise ValueError(f"Missing or out-of-root mirror source: {relative_path}")
    return candidate


def destination_path(relative_path: str) -> Path:
    candidate = (DESTINATION_ROOT / relative_path).resolve()
    if not candidate.is_relative_to(DESTINATION_ROOT.resolve()):
        raise ValueError(f"Unsafe mirror destination: {relative_path}")
    return candidate


def build_receipt(created_utc: str | None = None) -> dict[str, Any]:
    if not VAULT_ROOT.exists():
        raise ValueError(f"E-drive proof vault is unavailable: {VAULT_ROOT}")
    DESTINATION_ROOT.mkdir(parents=True, exist_ok=True)

    artifacts = []
    for relative_path in SOURCES:
        source = source_path(relative_path)
        destination = destination_path(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        source_hash = sha256_file(source)
        destination_hash = sha256_file(destination)
        if source_hash != destination_hash or source.stat().st_size != destination.stat().st_size:
            raise ValueError(f"Build Week mirror verification failed: {relative_path}")
        artifacts.append(
            {
                "source": relative_path,
                "destination": destination.as_posix(),
                "bytes": source.stat().st_size,
                "sha256": source_hash,
                "copy_sha256_matched": True,
            }
        )

    payload: dict[str, Any] = {
        "schema": "lumencore.openai_build_week_e_drive_sync_receipt.v1",
        "created_utc": created_utc or now_utc(),
        "destination_root": DESTINATION_ROOT.as_posix(),
        "artifact_count": len(artifacts),
        "all_sha256_matched_after_copy": True,
        "relative_paths_preserved": True,
        "private_files_mirrored": False,
        "browser_navigation_performed": False,
        "artifacts": artifacts,
        "claim_boundary": (
            "This receipt proves only that the listed public Build Week app, readiness, test, and "
            "hardware-concept artifacts were copied to the stated E-drive directory with matching "
            "SHA-256 hashes. It does not prove public deployment, Devpost registration, model identity, "
            "video publication, final submission, eligibility, judging outcome, endorsement, award, "
            "external validation, engineering performance, safety, patent rights, funding, or value."
        ),
        "receipt_copy_destination": (
            DESTINATION_ROOT
            / "grant_submissions/OPENAI_BUILD_WEEK_20260721"
            / RECEIPT.name
        ).as_posix(),
    }
    payload["receipt_payload_sha256"] = stable_hash(payload)
    return payload


def write_and_mirror_receipt(payload: dict[str, Any]) -> None:
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    destination = Path(payload["receipt_copy_destination"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RECEIPT, destination)
    if sha256_file(RECEIPT) != sha256_file(destination):
        raise ValueError("Build Week receipt self-copy hash mismatch")


def main() -> int:
    payload = build_receipt()
    write_and_mirror_receipt(payload)
    print(
        json.dumps(
            {
                "status": "OPENAI_BUILD_WEEK_E_DRIVE_MIRROR_VERIFIED",
                "artifact_count": payload["artifact_count"],
                "destination_root": payload["destination_root"],
                "receipt_payload_sha256": payload["receipt_payload_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
