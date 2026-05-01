import numpy as np
import pandas as pd

def _s(x):
    s = pd.Series(x).astype(float).replace([np.inf, -np.inf], np.nan)
    return s.ffill().bfill().fillna(0.0)

def _norm(x):
    s = _s(x)
    m = float(np.nanmean(np.abs(s.values)))
    if not np.isfinite(m) or m <= 1e-12:
        return pd.Series(np.zeros(len(s)), index=s.index, dtype=float)
    return s / m

# =========================================================
# 1. CROSS-ASSET RESONANCE
# =========================================================
def algo_cross_asset_resonance(r):
    s = _s(r)
    fast = _norm(s.rolling(5).mean())
    mid = _norm(s.rolling(13).mean())
    slow = _norm(s.rolling(34).mean())
    out = (fast * mid) + (mid * slow) + (fast * slow)
    return _norm(out).clip(-3, 3)

# =========================================================
# 2. MULTI-TIMEFRAME PER SYMBOL
# =========================================================
def algo_multi_timeframe_stack(r):
    s = _s(r)
    tf1 = _norm(s.rolling(5).mean())
    tf2 = _norm(s.rolling(21).mean())
    tf3 = _norm(s.rolling(55).mean())
    out = (tf1 + tf2 + tf3) / 3.0
    return _norm(out).clip(-3, 3)

# =========================================================
# 3. UNIVERSE-LEVEL CONSENSUS VOTING
# =========================================================
def algo_universe_consensus_vote(r):
    s = _s(r)
    a = np.sign(s.rolling(5).mean())
    b = np.sign(s.rolling(13).mean())
    c = np.sign(s.rolling(34).mean())
    d = np.sign(s.diff(3).fillna(0.0))
    out = (a + b + c + d) / 4.0
    return _norm(out).clip(-1, 1)

# =========================================================
# 4. CHAMPION-OF-CHAMPIONS META-ROUTER
# =========================================================
def algo_champion_meta_router(r):
    s = _s(r)
    trend = _norm(s.rolling(8).mean() - s.rolling(34).mean())
    pressure = _norm(s.diff(5).fillna(0.0))
    entropy = _norm(-(s.rolling(21).std() / (s.abs().rolling(21).mean() + 1e-9)).fillna(0.0))
    out = (trend + pressure + entropy) / 3.0
    return _norm(out).clip(-3, 3)

ALGO_WRAPPERS = {
    "cross_asset_resonance": algo_cross_asset_resonance,
    "multi_timeframe_stack": algo_multi_timeframe_stack,
    "universe_consensus_vote": algo_universe_consensus_vote,
    "champion_meta_router": algo_champion_meta_router,
}

# =========================================================
# META STRATEGIES
# =========================================================
def strat_cross_asset_gate(x):
    s = _s(x)
    sig = np.where(s > 0.35, 1.0, np.where(s < -0.35, -1.0, 0.0))
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_multi_timeframe_follow(x):
    s = _s(x)
    fast = s.rolling(5).mean()
    slow = s.rolling(21).mean()
    sig = np.sign(fast - slow)
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_universe_vote_break(x):
    s = _s(x)
    sig = np.where(s > 0.5, 1.0, np.where(s < -0.5, -1.0, 0.0))
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_champion_router(x):
    s = _s(x)
    z = (s - s.rolling(34).mean()) / (s.rolling(34).std() + 1e-9)
    sig = np.where(z > 1.0, 1.0, np.where(z < -1.0, -1.0, 0.0))
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

STRATEGIES = {
    "cross_asset_gate": strat_cross_asset_gate,
    "multi_timeframe_follow": strat_multi_timeframe_follow,
    "universe_vote_break": strat_universe_vote_break,
    "champion_router": strat_champion_router,
}

# =========================================================
# META METRIC PROFILES
# =========================================================
METRIC_PROFILES = {
    "meta_router": {
        "test_sharpe": 4.0,
        "test_calmar": 2.0,
        "test_expectancy": 180.0,
        "test_win_rate": 1.5,
        "stability": 2.5,
        "test_vs_baseline": 4.0,
        "test_max_dd_penalty": 4.0,
        "test_vol_penalty": 0.4,
    },
    "consensus_heavy": {
        "test_sharpe": 3.0,
        "test_calmar": 2.0,
        "test_expectancy": 120.0,
        "test_win_rate": 2.0,
        "stability": 3.0,
        "test_vs_baseline": 2.5,
        "test_max_dd_penalty": 5.0,
        "test_vol_penalty": 0.5,
    },
}
