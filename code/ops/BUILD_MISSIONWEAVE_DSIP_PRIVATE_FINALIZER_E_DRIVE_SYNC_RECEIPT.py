from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "MISSIONWEAVE_DSIP_PRIVATE_FINALIZER_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
DESTINATION_ROOT = Path(
    "E:/LumaProofVault/SUBMISSIONS/MISSIONWEAVE_DSIP_PRIVATE_FINALIZER_20260717"
)
RECEIPT_COPY = (
    DESTINATION_ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / RECEIPT.name
)
EXPECTED_SCHEMA = "lumencore.bounded_mirror_receipt.v1"
PRIVATE_PACKAGE_PREFIX = Path(
    "grant_submissions/DLA26BZ03_NV011_MissionWeave/private"
)
SOURCE_REPLACEMENTS = {
    "grant_submissions/funding_sprint_20260709/"
    "NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-17.md": (
        "grant_submissions/funding_sprint_20260709/"
        "NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-18.md"
    )
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def safe_source(relative_path: str) -> tuple[Path, Path]:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe mirror source path: {relative_path}")
    if is_within(relative, PRIVATE_PACKAGE_PREFIX):
        raise ValueError(f"Private MissionWeave artifact cannot be mirrored: {relative_path}")

    source = (ROOT / relative).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
        raise ValueError(f"Missing or out-of-root mirror source: {relative_path}")
    return relative, source


def safe_destination(relative: Path) -> Path:
    destination = (DESTINATION_ROOT / relative).resolve()
    if not destination.is_relative_to(DESTINATION_ROOT.resolve()):
        raise ValueError(f"Unsafe mirror destination: {relative.as_posix()}")
    return destination


def artifact_sources(existing: dict[str, Any]) -> list[str]:
    if existing.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("Existing MissionWeave receipt has the wrong schema")
    if existing.get("public_neutral_package_only") is not True:
        raise ValueError("MissionWeave receipt is not bounded to the public neutral package")
    for key in (
        "private_input_mirrored",
        "private_assigned_number_artifacts_mirrored",
        "private_values_or_credentials_mirrored",
    ):
        if existing.get(key) is not False:
            raise ValueError(f"MissionWeave private-mirror boundary is not closed: {key}")

    sources = [
        SOURCE_REPLACEMENTS.get(str(row.get("source")), str(row.get("source")))
        for row in existing.get("artifacts", [])
        if isinstance(row, dict) and row.get("source")
    ]
    if not sources or len(sources) != len(set(sources)):
        raise ValueError("MissionWeave receipt sources are empty or duplicated")
    for source in sources:
        safe_source(source)
    return sources


def build_receipt(generated_utc: str | None = None) -> dict[str, Any]:
    if not DESTINATION_ROOT.parent.exists():
        raise ValueError(f"E-drive proof-vault parent is unavailable: {DESTINATION_ROOT.parent}")

    existing = read_json(RECEIPT)
    sources = artifact_sources(existing)
    DESTINATION_ROOT.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, Any]] = []
    for source_name in sources:
        relative, source = safe_source(source_name)
        destination = safe_destination(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        source_hash = sha256_file(source)
        destination_hash = sha256_file(destination)
        if source_hash != destination_hash or source.stat().st_size != destination.stat().st_size:
            raise ValueError(f"MissionWeave mirror verification failed: {source_name}")
        artifacts.append(
            {
                "source": relative.as_posix(),
                "destination": destination.as_posix(),
                "bytes": source.stat().st_size,
                "sha256": source_hash,
                "copy_sha256_matched": True,
            }
        )

    payload = dict(existing)
    payload.update(
        {
            "generated_utc": generated_utc or now_utc(),
            "destination_root": DESTINATION_ROOT.as_posix(),
            "artifact_count": len(artifacts),
            "all_sha256_matched_after_copy": True,
            "artifacts": artifacts,
        }
    )
    return payload


def write_and_mirror_receipt(payload: dict[str, Any]) -> None:
    RECEIPT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    RECEIPT_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RECEIPT, RECEIPT_COPY)
    if sha256_file(RECEIPT) != sha256_file(RECEIPT_COPY):
        raise ValueError("MissionWeave receipt self-copy hash mismatch")


def main() -> int:
    payload = build_receipt()
    write_and_mirror_receipt(payload)
    print(
        json.dumps(
            {
                "status": "MISSIONWEAVE_PUBLIC_MIRROR_VERIFIED",
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
