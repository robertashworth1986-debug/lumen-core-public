from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_rebuild_engine_logic_keeps_paper_runtime_kill_switch_on():
    text = (ROOT / "code" / "execution" / "rebuild_engine_logic.py").read_text(encoding="utf-8")

    assert 'runtime["mode"] = "paper"' in text
    assert 'runtime["allow_live_orders"] = False' in text
    assert 'runtime["paper_enabled"] = True' in text
    assert 'runtime["kill_switch"] = True' in text


def test_full_truth_orchestrator_disarms_non_locked_runtime():
    text = (ROOT / "code" / "FULL_TRUTH_ORCHESTRATOR.py").read_text(encoding="utf-8")

    assert 'rt["kill_switch"] = not strict_live_locked' in text
    assert 'ex_rt["kill_switch"] = not strict_live_locked' in text
    assert 'ex_status["kill_switch"] = not strict_live_locked' in text
