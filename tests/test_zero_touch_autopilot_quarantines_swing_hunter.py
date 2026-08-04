from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "code" / "RUN_ZERO_TOUCH_AUTOPILOT.ps1"


def test_zero_touch_autopilot_never_restarts_the_quarantined_swing_hunter():
    text = RUNNER.read_text(encoding="utf-8")

    assert "Legacy swing hunter is quarantined and will not be launched" in text
    assert 'ArgumentList ".\\\\kraken_swing_hunter.py"' not in text
