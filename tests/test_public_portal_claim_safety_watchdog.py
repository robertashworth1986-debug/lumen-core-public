from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "WATCH_PUBLIC_PORTAL_CLAIM_SAFETY.py"
SPEC = importlib.util.spec_from_file_location("portal_claim_safety_watchdog", MODULE_PATH)
assert SPEC and SPEC.loader
watchdog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watchdog)


def test_stale_or_incomplete_portal_requires_repair() -> None:
    assert watchdog.portal_needs_repair("Reviewer-Safe Winner State")
    assert watchdog.portal_needs_repair("No Current Performance Champion")


def test_current_claim_safe_portal_does_not_require_repair() -> None:
    text = "\n".join(watchdog.REQUIRED_MARKERS)
    assert not watchdog.portal_needs_repair(text)
