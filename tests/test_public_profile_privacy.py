from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EIN_PATTERN = re.compile(r"\b\d{2}-\d{7}\b")
PRIVATE_APPLICATION_PATTERN = re.compile(r"\b\d{2}/\d{3},\d{3}\b")


def test_public_grants_profile_contains_no_private_contact_or_tax_values() -> None:
    profile = json.loads((ROOT / "code" / "grants_profile_lumencore.json").read_text(encoding="utf-8"))
    organization = profile["organization"]
    contacts = profile["contacts"]

    assert organization["ein"] == ""
    assert contacts["authorized_rep"]["email"] == ""
    assert contacts["authorized_rep"]["phone"] == ""
    assert contacts["project_director"]["email"] == ""
    assert contacts["project_director"]["phone"] == ""


def test_public_identity_surfaces_exclude_tax_and_private_application_patterns() -> None:
    paths = [
        ROOT / "code" / "grants_profile_lumencore.json",
        ROOT / "code" / "build_booth_explainer_brief.py",
        ROOT / "code" / "build_lumencore_universe_map.py",
        ROOT / "code" / "luma_experience_gateway.py",
        ROOT / "INVESTOR_BRIEF.md",
        ROOT / "docs" / "LUMAJARVIS_OPERATING_MEMORY_2026-06-20.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert EIN_PATTERN.search(combined) is None
    assert PRIVATE_APPLICATION_PATTERN.search(combined) is None
