from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PRIVATE_DIR = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "private"
)
DEFAULT_RECEIPT = PRIVATE_DIR / "MISSIONWEAVE_JCP_EVIDENCE_RECEIPT.private.json"

SCHEMA = "lumencore.missionweave_jcp_evidence_private.v1"
TOPIC = "DLA26BZ03-NV011"
EVIDENCE_FILENAMES = {
    "JCP_APPLICATION_SUBMISSION_RECEIPT": (
        "MISSIONWEAVE_JCP_APPLICATION_SUBMISSION_RECEIPT.private.pdf"
    ),
    "CERTIFIED_DD2345": "MISSIONWEAVE_CERTIFIED_DD2345.private.pdf",
}


class JcpEvidenceCaptureError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise JcpEvidenceCaptureError("INVALID_AWARE_TIMESTAMP") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise JcpEvidenceCaptureError("INVALID_AWARE_TIMESTAMP")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def inspect_official_pdf(path: Path) -> dict[str, Any]:
    candidate = path.expanduser().resolve()
    if path.is_symlink() or not candidate.is_file():
        raise JcpEvidenceCaptureError("EVIDENCE_FILE_NOT_REGULAR")
    size = candidate.stat().st_size
    if size <= 8:
        raise JcpEvidenceCaptureError("EVIDENCE_PDF_EMPTY")
    with candidate.open("rb") as handle:
        header = handle.read(5)
    if header != b"%PDF-":
        raise JcpEvidenceCaptureError("EVIDENCE_FILE_NOT_PDF")
    return {
        "path": candidate,
        "bytes": size,
        "sha256": sha256_file(candidate),
    }


def build_receipt(
    *,
    evidence_kind: str,
    evidence_sha256: str,
    source_issued_utc: str | datetime,
    captured_utc: str | datetime,
    entity_match_confirmed: bool,
    corporate_official_reviewed: bool,
) -> dict[str, Any]:
    if evidence_kind not in EVIDENCE_FILENAMES:
        raise JcpEvidenceCaptureError("EVIDENCE_KIND_INVALID")
    if (
        not isinstance(evidence_sha256, str)
        or len(evidence_sha256) != 64
        or any(ch not in "0123456789ABCDEFabcdef" for ch in evidence_sha256)
    ):
        raise JcpEvidenceCaptureError("EVIDENCE_SHA256_INVALID")
    if not entity_match_confirmed:
        raise JcpEvidenceCaptureError("ENTITY_MATCH_CONFIRMATION_REQUIRED")
    if not corporate_official_reviewed:
        raise JcpEvidenceCaptureError("CORPORATE_REVIEW_CONFIRMATION_REQUIRED")

    return {
        "captured_utc": iso_z(parse_utc(captured_utc)),
        "corporate_official_reviewed": True,
        "entity_match_confirmed": True,
        "evidence_file": EVIDENCE_FILENAMES[evidence_kind],
        "evidence_file_sha256": evidence_sha256.upper(),
        "evidence_kind": evidence_kind,
        "schema": SCHEMA,
        "source_channel": "JCP_PORTAL",
        "source_issued_utc": iso_z(parse_utc(source_issued_utc)),
        "topic": TOPIC,
    }


def _inside(path: Path, parent: Path) -> bool:
    return path.resolve().is_relative_to(parent.resolve())


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _copy_pdf(source: Path, destination: Path, *, replace_existing: bool) -> None:
    if source.resolve() == destination.resolve():
        return
    if destination.exists():
        existing_hash = sha256_file(destination)
        source_hash = sha256_file(source)
        if existing_hash == source_hash:
            return
        if not replace_existing:
            raise JcpEvidenceCaptureError("PRIVATE_EVIDENCE_ALREADY_EXISTS_DIFFERENT")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(source, temporary)
        if sha256_file(temporary) != sha256_file(source):
            raise JcpEvidenceCaptureError("PRIVATE_EVIDENCE_COPY_HASH_MISMATCH")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def persist_private_bundle(
    *,
    evidence_source: Path,
    evidence_kind: str,
    source_issued_utc: str | datetime,
    captured_utc: str | datetime,
    entity_match_confirmed: bool,
    corporate_official_reviewed: bool,
    private_dir: Path = PRIVATE_DIR,
    receipt_path: Path = DEFAULT_RECEIPT,
    replace_existing: bool = False,
    enforce_canonical_private_dir: bool = True,
) -> dict[str, Any]:
    requested_private_dir = private_dir.expanduser()
    requested_receipt_path = receipt_path.expanduser()
    if requested_private_dir.is_symlink() or requested_receipt_path.is_symlink():
        raise JcpEvidenceCaptureError("PRIVATE_TARGET_SYMLINK_REJECTED")

    private_dir = requested_private_dir.resolve()
    receipt_path = requested_receipt_path.resolve()
    if enforce_canonical_private_dir:
        if private_dir != PRIVATE_DIR.resolve() or not _inside(receipt_path, PRIVATE_DIR):
            raise JcpEvidenceCaptureError("PRIVATE_TARGET_OUTSIDE_CANONICAL_DIR")
    elif not _inside(receipt_path, private_dir):
        raise JcpEvidenceCaptureError("PRIVATE_TARGET_OUTSIDE_PRIVATE_DIR")
    evidence = inspect_official_pdf(evidence_source)
    receipt = build_receipt(
        evidence_kind=evidence_kind,
        evidence_sha256=evidence["sha256"],
        source_issued_utc=source_issued_utc,
        captured_utc=captured_utc,
        entity_match_confirmed=entity_match_confirmed,
        corporate_official_reviewed=corporate_official_reviewed,
    )
    destination = private_dir / receipt["evidence_file"]
    if not _inside(destination, private_dir):
        raise JcpEvidenceCaptureError("PRIVATE_EVIDENCE_TARGET_INVALID")

    receipt_bytes = (
        json.dumps(receipt, indent=2, ensure_ascii=True) + "\n"
    ).encode("utf-8")
    if receipt_path.exists():
        if receipt_path.read_bytes() != receipt_bytes and not replace_existing:
            raise JcpEvidenceCaptureError("PRIVATE_RECEIPT_ALREADY_EXISTS_DIFFERENT")

    _copy_pdf(evidence["path"], destination, replace_existing=replace_existing)
    if sha256_file(destination) != receipt["evidence_file_sha256"]:
        raise JcpEvidenceCaptureError("PRIVATE_EVIDENCE_FINAL_HASH_MISMATCH")
    _atomic_write(receipt_path, receipt_bytes)

    return {
        "schema": SCHEMA,
        "evidence_kind": evidence_kind,
        "evidence_bytes": evidence["bytes"],
        "evidence_integrity_pass": True,
        "entity_match_confirmed": True,
        "corporate_official_reviewed": True,
        "private_path_redacted": True,
        "private_hash_redacted": True,
        "receipt_written": receipt_path.is_file(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture an official MissionWeave JCP/DD Form 2345 PDF into the ignored "
            "private evidence area without printing its path or hash."
        )
    )
    parser.add_argument("--evidence-file", type=Path)
    parser.add_argument(
        "--evidence-kind",
        choices=sorted(EVIDENCE_FILENAMES),
    )
    parser.add_argument("--source-issued-utc")
    parser.add_argument("--captured-utc")
    parser.add_argument("--confirm-entity-match", action="store_true")
    parser.add_argument("--confirm-corporate-review", action="store_true")
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument(
        "--check-target",
        action="store_true",
        help="Check that the ignored private destination is safe without reading it.",
    )
    args = parser.parse_args()

    if args.check_target:
        safe = bool(
            PRIVATE_DIR.parent.is_dir()
            and not PRIVATE_DIR.is_symlink()
            and _inside(DEFAULT_RECEIPT, PRIVATE_DIR)
        )
        print(
            json.dumps(
                {
                    "private_target_safe": safe,
                    "private_path_redacted": True,
                    "private_contents_read": False,
                },
                indent=2,
            )
        )
        return 0 if safe else 1

    required = {
        "--evidence-file": args.evidence_file,
        "--evidence-kind": args.evidence_kind,
        "--source-issued-utc": args.source_issued_utc,
    }
    missing = [flag for flag, value in required.items() if not value]
    if missing:
        parser.error("required unless --check-target: " + ", ".join(missing))

    captured = args.captured_utc or datetime.now(timezone.utc)
    result = persist_private_bundle(
        evidence_source=args.evidence_file,
        evidence_kind=args.evidence_kind,
        source_issued_utc=args.source_issued_utc,
        captured_utc=captured,
        entity_match_confirmed=args.confirm_entity_match,
        corporate_official_reviewed=args.confirm_corporate_review,
        replace_existing=args.replace_existing,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
