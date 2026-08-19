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

    assert "validate_live_action_authority" in text
    assert "human_action_time_authority" in text
    assert 'rt["kill_switch"] = True' in text
    assert "if not strict_live_locked:" in text
    assert 'reason="full_truth_fail_closed_paper_sync"' in text
    assert 'ex_rt["kill_switch"] = not strict_live_locked' in text
    assert 'ex_status["kill_switch"] = not strict_live_locked' in text
    assert 'ex_status["canonical_runtime_rewritten"] = canonical_runtime_rewritten' in text


def test_activity_collector_has_separate_state_and_refreshes_reconciliation():
    text = (ROOT / "code" / "alpaca_paper_loop_builder.py").read_text(encoding="utf-8")

    assert 'COLLECTOR_STATE_FILE = OUT / "execution" / "alpaca_activity_collector_state.json"' in text
    assert 'load_json(COLLECTOR_STATE_FILE, {})' in text
    assert 'write_json(COLLECTOR_STATE_FILE, state)' in text
    assert 'STATE_FILE  = OUT / "paper_trade_state.json"' not in text
    assert '"seen_fill_id_sha256"' in text
    assert 'BUILD_PAPER_LEDGER_RECONCILIATION.py' in text
    assert '"ledger_reconciliation_status": reconciliation_status' in text
