import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "execution" / "signal_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("signal_gate_reproducibility", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fully_populated_input(module):
    return module.GateInput(
        regime="normal",
        regime_confidence=0.9,
        alignment_score=0.9,
        liquidity_score=0.9,
        signal_decay_score=0.1,
        cross_confirm_score=0.9,
        expected_edge_bps=25.0,
        direction_hint=0.7,
        volatility_pct=1.0,
        correlation_to_portfolio=0.1,
        market_regime="normal",
        sector_heat=0.1,
        historical_win_rate=0.7,
        orderbook_spread_bps=1.0,
        orderbook_depth_usd=100_000.0,
        orderbook_imbalance=0.1,
        onchain_tx_volume_usd=1_000_000.0,
        onchain_gas_fee_usd=1.0,
        onchain_whale_tx_count=10,
    )


def decision_history_row(index: int) -> dict:
    return {
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=60 - index)).isoformat(),
        "inputs": {
            "alignment_score": 0.4 + (index % 3) * 0.2,
            "regime_confidence": 0.5,
            "liquidity_score": 0.6,
            "cross_confirm_score": 0.7,
            "expected_edge_bps": 5.0 + index,
            "volatility_pct": 1.0,
            "correlation_to_portfolio": 0.1,
            "sector_heat": 0.1,
            "signal_decay_score": 0.1,
            "historical_win_rate": 0.5,
            "monte_carlo_edge": 0.5,
            "live_data_freshness": 1.0,
        },
        "profitable": bool(index % 2),
    }


def test_monte_carlo_and_gate_decision_are_deterministic():
    module = load_module()
    price_series = pd.Series(np.linspace(100.0, 120.0, 160))
    first = module.EvolutionarySignalGate(monte_carlo_simulations=100, random_seed=17)
    second = module.EvolutionarySignalGate(monte_carlo_simulations=100, random_seed=17)

    first_decision = first.decide(fully_populated_input(module), price_series)
    second_decision = second.decide(fully_populated_input(module), price_series)

    assert first_decision == second_decision


def test_adaptation_is_opt_in_and_does_not_train_by_default():
    module = load_module()
    gate = module.EvolutionarySignalGate()
    gate.decision_history = [decision_history_row(index) for index in range(60)]

    assert gate._adapt_thresholds_ml() == gate.base_thresholds
    assert gate.ml_trained is False


def test_opt_in_adaptation_requires_a_temporally_valid_training_window():
    module = load_module()
    gate = module.EvolutionarySignalGate(adaptation_enabled=True)
    gate.decision_history = [decision_history_row(index) for index in range(60)]

    adapted = gate._adapt_thresholds_ml()

    assert gate.ml_trained is True
    assert set(adapted) == set(gate.base_thresholds)


def test_opt_in_adaptation_rejects_a_single_outcome_training_window():
    module = load_module()
    gate = module.EvolutionarySignalGate(adaptation_enabled=True)
    gate.decision_history = [decision_history_row(index) for index in range(60)]
    for row in gate.decision_history:
        row["profitable"] = True

    assert gate._adapt_thresholds_ml() == gate.base_thresholds
    assert gate.ml_trained is False
