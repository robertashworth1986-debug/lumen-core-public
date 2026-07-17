#!/usr/bin/env python3
"""Create and verify the bounded MissionWeave submission-package manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "MISSIONWEAVE_DSIP_PACKAGE_MANIFEST_2026-07-16.json"

PACKAGE_FILES = [
    "MISSIONWEAVE_DSIP_ASSEMBLY_MAP_2026-07-16.md",
    "MISSIONWEAVE_DSIP_VOLUME1_PUBLIC_TEXT_2026-07-16.md",
    "MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.md",
    "MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.docx",
    "MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.pdf",
    "MISSIONWEAVE_DSIP_VOLUME2_BUILD_METADATA_2026-07-16.json",
    "MISSIONWEAVE_DSIP_VOLUME3_COST_INPUTS_2026-07-16.md",
    "MISSIONWEAVE_DSIP_VOLUME5_WORKSHEET_2026-07-16.md",
    "MISSIONWEAVE_CLAIM_EVIDENCE_MATRIX_2026-07-16.md",
    "MISSIONWEAVE_BOUNDED_PROCESS_PLAN_2026-06-19.md",
    "build_missionweave_dsip_volume2_candidate.py",
    "build_missionweave_package_manifest.py",
    "source_attachments/DLA_26BZ_RELEASE_3_COMPONENT_INSTRUCTIONS.pdf",
    "source_attachments/DLA26BZ03_NV011_OFFICIAL_TOPIC_DETAILS.json",
    "source_attachments/DoW_2026_SBIR_BAA_RELEASE_3_AMENDMENT_2.pdf",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_manifest(root: Path, output: Path) -> dict:
    files = []
    for relative in PACKAGE_FILES:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        files.append(
            {
                "path": relative.replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "schema": "missionweave_dsip_submission_package_manifest.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "topic": "DLA26BZ03-NV011",
        "deadline": "2026-07-22T12:00:00-04:00",
        "applicant": "Robert Ashworth d/b/a LumenCore",
        "package_state": "portal-ready candidate; certification and final submission gates remain",
        "file_count": len(files),
        "files": files,
        "claim_boundary": (
            "Generated-workflow feasibility evidence only. The package does not establish DLA "
            "operational performance, field validation, causal workforce impact, production "
            "readiness, realized savings, CMMC assessment, export-control certification, patent "
            "validity, independent reproduction, or a 10x improvement."
        ),
    }
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_manifest(root: Path, manifest: dict) -> None:
    for item in manifest["files"]:
        path = root / item["path"]
        if path.stat().st_size != item["bytes"]:
            raise ValueError(f"Size mismatch: {item['path']}")
        if sha256(path) != item["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {item['path']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        manifest = json.loads(args.output.read_text(encoding="utf-8"))
        verify_manifest(args.root, manifest)
        print(f"verified {manifest['file_count']} files")
    else:
        manifest = build_manifest(args.root, args.output)
        verify_manifest(args.root, manifest)
        print(f"wrote and verified {manifest['file_count']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
