from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "RUN_BOOTH_WARROOM_REFRESH.ps1"


def test_warroom_autopilot_is_opt_in_and_human_unlocked() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "[switch]$ArmAutopilot" in text
    assert "if ($ArmAutopilot -and -not $SkipAutopilot)" in text
    assert "$env:LUMA_HUMAN_UNLOCK_TOKEN" in text
    assert "Autopilot skipped (safe default" in text
