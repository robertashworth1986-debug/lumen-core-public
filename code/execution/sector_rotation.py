# sector_rotation.py
"""
Sector/Theme Rotation and Regime Detection Module
- Maps each symbol to a sector/theme
- Tracks rolling performance by sector
- Detects market regime (trend, mean-reversion, high/low vol)
- Outputs best sector/theme and current regime for orchestrator and RL policy
"""
import numpy as np
import pandas as pd
from collections import defaultdict, deque
from datetime import datetime

SECTOR_MAP = {
    'BTC': 'crypto',
    'ETH': 'crypto',
    'SOL': 'crypto',
    'ADA': 'crypto',
    'XRP': 'crypto',
    'DOGE': 'crypto',
    'AAPL': 'equity',
    'MSFT': 'equity',
    'TSLA': 'equity',
    'SPY': 'etf',
    'QQQ': 'etf',
    # ... extend as needed
}

class SectorRotation:
    def __init__(self):
        self.sector_perf = defaultdict(lambda: deque(maxlen=100))
        self.last_regime = 'normal'

    def update(self, symbol, pnl):
        sector = SECTOR_MAP.get(symbol, 'other')
        self.sector_perf[sector].append(pnl)

    def best_sector(self):
        avg_perf = {s: np.mean(list(p)) for s, p in self.sector_perf.items() if len(p) > 10}
        if not avg_perf:
            return 'crypto'
        return max(avg_perf, key=avg_perf.get)

    def detect_regime(self, returns):
        # returns: pd.Series of recent returns
        vol = returns.rolling(24).std().iloc[-1]
        mean = returns.rolling(24).mean().iloc[-1]
        if vol > 0.05:
            regime = 'high_vol'
        elif abs(mean) > 0.01:
            regime = 'trend'
        else:
            regime = 'mean_revert'
        self.last_regime = regime
        return regime
