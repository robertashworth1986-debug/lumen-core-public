# rl_policy.py
"""
Reinforcement Learning Policy Layer for Adaptive Risk and Family Selection
- Uses a simple Q-learning table for state-action values
- State: (symbol, family, recent_sharpe, win_rate, drawdown, regime)
- Action: (risk fraction, family selection, sizing multiplier)
- Reward: realized PnL, Sharpe improvement, win/loss
- Updates Q-table after each trade
"""
import json
import numpy as np
from pathlib import Path

RL_POLICY_FILE = Path("C:/LumaTrader/rl_policy_qtable.json")

class RLPolicy:
    def __init__(self):
        self.q_table = {}
        self.load()

    def state_key(self, symbol, family, sharpe, win_rate, drawdown, regime):
        # Discretize for table
        return f"{symbol}|{family}|{int(sharpe*10)}|{int(win_rate*100)}|{int(drawdown*100)}|{regime}"

    def action_space(self):
        # (risk fraction, sizing multiplier)
        return [(r, s) for r in [0.2, 0.5, 0.8, 1.0] for s in [0.5, 1.0, 1.5, 2.0]]

    def select_action(self, symbol, family, sharpe, win_rate, drawdown, regime, epsilon=0.1):
        """
        Always returns a tuple (risk_fraction, sizing_multiplier).
        If anything goes wrong, returns (0.2, 1.0) as a safe default.
        """
        try:
            state = self.state_key(symbol, family, sharpe, win_rate, drawdown, regime)
            actions = self.action_space()
            if not actions:
                return (0.2, 1.0)
            if np.random.rand() < epsilon or state not in self.q_table:
                action = actions[np.random.randint(len(actions))]
            else:
                qvals = self.q_table[state]
                idx = int(np.argmax(qvals)) if qvals and len(qvals) == len(actions) else 0
                action = actions[idx]
            # Defensive: ensure tuple of length 2
            if isinstance(action, (list, tuple)) and len(action) == 2:
                return tuple(action)
            return (0.2, 1.0)
        except Exception:
            return (0.2, 1.0)

    def update(self, symbol, family, sharpe, win_rate, drawdown, regime, action, reward, alpha=0.2, gamma=0.95):
        state = self.state_key(symbol, family, sharpe, win_rate, drawdown, regime)
        actions = self.action_space()
        if state not in self.q_table:
            self.q_table[state] = [0.0 for _ in actions]
        idx = actions.index(action)
        old_q = self.q_table[state][idx]
        self.q_table[state][idx] = old_q + alpha * (reward + gamma * max(self.q_table[state]) - old_q)
        self.save()

    def save(self):
        RL_POLICY_FILE.write_text(json.dumps(self.q_table), encoding="utf-8")

    def load(self):
        if RL_POLICY_FILE.exists():
            try:
                self.q_table = json.loads(RL_POLICY_FILE.read_text(encoding="utf-8"))
            except Exception:
                self.q_table = {}
        else:
            self.q_table = {}
