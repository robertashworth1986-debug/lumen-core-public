"""Integrity checks for the frozen FALCON solicitation inputs."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "grant_submissions" / "DPA26BZ04_DV016_FALCON"
SOURCE_DIR = PACKAGE / "source_attachments"
SOURCE_MANIFEST = PACKAGE / "DPA26BZ04_DV016_SOURCE_MANIFEST_2026-07-15.md"

EXPECTED_FILES = {
    "FALCON_FAQ_2026-07-13.pdf": (
        144_816,
        "6C8727E59FAF69FEB2717987C45E6BC8901D3B046D25EBFA4E4998A9C12A1C41",
    ),
    "DARPA_DP2_VOLUME2_TEMPLATE_2026-07.docx": (
        1_631_239,
        "D545CF7F5E0BB4AA773D873443A43C0DD803FC63E06514C4B1074E80B09399A6",
    ),
    "DARPA_DP2_VOLUME3_COST_TEMPLATE_2024-07-09.xlsx": (
        565_182,
        "CDD372D8E0A4ACE372953F50CBF1D16C8A01C9BA6CF498B3D6B07D1DE0CC3E7B",
    ),
    "DARPA_TECHNICAL_SUMMARY_QUAD_CHART_TEMPLATE_2025-01.pptx": (
        437_191,
        "85A01CC3C38CE461B69A94DE756B6A274682352DDE55E3B327B93FEB2AED5CEB",
    ),
    "DARPA_PHASE_II_PROPOSAL_INSTRUCTIONS_2026-01-30.pdf": (
        389_194,
        "DDB0541EE2F453E4F9295B7655178BD16DE292788BF62C2564DC0F6F762039CB",
    ),
    "DoW_2026_SBIR_BAA_RELEASE_4_PREFACE.pdf": (
        683_438,
        "8633124410E5A0D1B1F1ECCDDD98F8C07D8368715E062A6C773A36E87AF73659",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


class FalconSourceManifestTests(unittest.TestCase):
    def test_frozen_source_files_match_declared_bytes_and_hashes(self) -> None:
        actual_names = {path.name for path in SOURCE_DIR.iterdir() if path.is_file()}
        self.assertEqual(actual_names, set(EXPECTED_FILES))
        for name, (expected_bytes, expected_hash) in EXPECTED_FILES.items():
            with self.subTest(name=name):
                path = SOURCE_DIR / name
                self.assertEqual(path.stat().st_size, expected_bytes)
                self.assertEqual(sha256(path), expected_hash)

    def test_manifest_records_every_frozen_source(self) -> None:
        text = SOURCE_MANIFEST.read_text(encoding="utf-8")
        for name, (expected_bytes, expected_hash) in EXPECTED_FILES.items():
            with self.subTest(name=name):
                self.assertIn(f"`source_attachments/{name}`", text)
                self.assertIn(f"| {expected_bytes} |", text)
                self.assertIn(f"`{expected_hash}`", text)

    def test_manifest_preserves_deadline_and_claim_boundaries(self) -> None:
        text = SOURCE_MANIFEST.read_text(encoding="utf-8")
        self.assertIn("Proposal type: Direct to Phase II only", text)
        self.assertIn("Open date: 2026-07-22", text)
        self.assertIn("Close date: 2026-08-19 at 12:00 PM Eastern Time", text)
        self.assertIn("not a submission, certification, eligibility determination", text)
        self.assertIn("Do not infer or pre-answer legal certifications", text)


if __name__ == "__main__":
    unittest.main()
