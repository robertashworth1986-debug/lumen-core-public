from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
RECEIPT = PACKAGE / "NASHVILLE_EC_FINANCIAL_AID_E_DRIVE_SYNC_RECEIPT_2026-07-20.json"
DESTINATION_ROOT = Path(
    "E:/LumaProofVault/SUBMISSIONS/NASHVILLE_EC_FINANCIAL_AID_20260720"
)
RECEIPT_COPY = DESTINATION_ROOT / RECEIPT.relative_to(ROOT)

PUBLIC_SOURCES = (
    "code/ops/BUILD_NASHVILLE_EC_FINANCIAL_AID_ACTION.py",
    "code/ops/BUILD_NASHVILLE_EC_FINANCIAL_AID_E_DRIVE_SYNC_RECEIPT.py",
    "code/ops/BUILD_EMAIL_ACTION_RECONCILIATION.py",
    "code/ops/BUILD_OUTREACH_FOLLOWUP_ACTION_QUEUE.py",
    "code/ops/BUILD_EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER.py",
    "config/outreach_followup_policies_v1.json",
    "tests/test_nashville_ec_financial_aid_action.py",
    "tests/test_nashville_ec_financial_aid_e_drive_sync_receipt.py",
    "tests/test_email_action_reconciliation.py",
    "tests/test_outreach_followup_action_queue.py",
    "tests/test_external_engagement_response_register.py",
    "grant_submissions/NASHVILLE_EC_FALL_2026/"
    "NASHVILLE_EC_FINANCIAL_AID_ACTION_2026-07-20.json",
    "grant_submissions/NASHVILLE_EC_FALL_2026/"
    "NASHVILLE_EC_FINANCIAL_AID_ACTION_2026-07-20.md",
    "grant_submissions/funding_sprint_20260709/"
    "EMAIL_ACTION_RECONCILIATION_2026-07-18.json",
    "grant_submissions/funding_sprint_20260709/"
    "EMAIL_ACTION_RECONCILIATION_2026-07-18.md",
    "grant_submissions/funding_sprint_20260709/"
    "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json",
    "grant_submissions/funding_sprint_20260709/"
    "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.md",
    "grant_submissions/funding_sprint_20260709/"
    "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-18.json",
    "grant_submissions/funding_sprint_20260709/"
    "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-18.md",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def safe_source(relative_name: str) -> tuple[Path, Path]:
    relative = Path(relative_name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe mirror source: {relative_name}")
    if "private" in {part.casefold() for part in relative.parts}:
        raise ValueError(f"Private artifact cannot enter public mirror: {relative_name}")
    source = (ROOT / relative).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
        raise ValueError(f"Missing or out-of-root mirror source: {relative_name}")
    return relative, source


def safe_destination(relative: Path) -> Path:
    destination = (DESTINATION_ROOT / relative).resolve()
    if not destination.is_relative_to(DESTINATION_ROOT.resolve()):
        raise ValueError(f"Unsafe mirror destination: {relative.as_posix()}")
    return destination


def build_receipt(generated_utc: str | None = None) -> dict[str, Any]:
    if not DESTINATION_ROOT.parent.exists():
        raise ValueError(f"E-drive proof-vault parent is unavailable: {DESTINATION_ROOT.parent}")
    if len(PUBLIC_SOURCES) != len(set(PUBLIC_SOURCES)):
        raise ValueError("Public mirror source list contains duplicates")

    DESTINATION_ROOT.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    for source_name in PUBLIC_SOURCES:
        relative, source = safe_source(source_name)
        destination = safe_destination(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        source_hash = sha256_file(source)
        destination_hash = sha256_file(destination)
        if source_hash != destination_hash or source.stat().st_size != destination.stat().st_size:
            raise ValueError(f"Mirror verification failed: {source_name}")
        artifacts.append(
            {
                "source": relative.as_posix(),
                "destination": destination.as_posix(),
                "bytes": source.stat().st_size,
                "sha256": source_hash,
                "copy_sha256_matched": True,
            }
        )

    return {
        "schema": "lumencore.bounded_mirror_receipt.v1",
        "generated_utc": generated_utc or now_utc(),
        "destination_root": DESTINATION_ROOT.as_posix(),
        "artifact_count": len(artifacts),
        "all_sha256_matched_after_copy": True,
        "public_action_control_only": True,
        "private_founder_values_mirrored": False,
        "browser_navigation_performed": False,
        "artifacts": artifacts,
        "claim_boundary": (
            "This receipt proves only that the listed public Nashville EC financial-aid "
            "action-control, routing, test, and generated register artifacts were copied to "
            "the stated E-drive directory with matching SHA-256 hashes. It does not include "
            "private founder answers and does not prove form submission, financial-aid "
            "approval, accelerator selection, funding, endorsement, or external validation."
        ),
    }


def write_and_mirror_receipt(payload: dict[str, Any]) -> None:
    RECEIPT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    RECEIPT_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RECEIPT, RECEIPT_COPY)
    if sha256_file(RECEIPT) != sha256_file(RECEIPT_COPY):
        raise ValueError("Mirror receipt self-copy hash mismatch")


def main() -> int:
    payload = build_receipt()
    write_and_mirror_receipt(payload)
    print(
        json.dumps(
            {
                "status": "NASHVILLE_FINANCIAL_AID_PUBLIC_MIRROR_VERIFIED",
                "artifact_count": payload["artifact_count"],
                "destination_root": payload["destination_root"],
                "receipt": RECEIPT.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
