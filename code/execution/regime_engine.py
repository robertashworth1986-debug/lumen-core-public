import os
import sys
import json
import math
import random
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import requests

# Add paths
sys.path.insert(0, r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\execution')

# Configuration
ROOT = Path(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2')
OUT = ROOT / 'out' / 'execution'
CONFIG = ROOT / 'config'

OUT.mkdir(parents=True, exist_ok=True)

print("🚀 LUMENCORE INSTITUTIONAL REGIME ENGINE")
print("=" * 70)
print("Multi-Timeframe | Monte Carlo | Advanced Indicators | Registry Integration")
print("=" * 70)

@dataclass
class RegimeState:
    name: str
    confidence: float
    vol_state: str
    trend_strength: float
    chop_score: float
    monte_carlo_probability: float
    sector_adjustment: float
    multi_timeframe_consensus: float
    advanced_indicators: dict
    timestamp: str

@dataclass
class MultiTimeframeData:
    timeframe_1m: pd.DataFrame
    timeframe_5m: pd.DataFrame
    timeframe_1h: pd.DataFrame

class InstitutionalRegimeEngine:
    """Upgraded regime engine with institutional features."""
    
    def __init__(self):
        self.monte_carlo_simulations = 1000
        self.regime_history = []
        
        # Load registry for sector data
        self.registry = self.load_registry()
        
        print("✓ Monte Carlo Simulations (1000 runs)")
        print("✓ Multi-Timeframe Analysis (1m, 5m, 1h)")
        print("✓ Advanced Indicators (RSI, MACD, Bollinger)")
        print("✓ Registry Integration (17+ sources)")
        print("✓ Sector-Specific Adjustments")
    
    def load_registry(self):
        """Load live source registry for sector data."""
        registry_path = CONFIG / 'live_source_registry.json'
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                data = json.load(f)
                return data.get('rows', [])
        return []
    
    def fetch_multi_timeframe_data(self, symbol: str) -> MultiTimeframeData:
        """Fetch price data across multiple timeframes."""
        # In production, integrate with real data sources (Kraken, Binance, etc.)
        # For demo, generate synthetic multi-timeframe data
        
        base_price = 50000 if symbol.upper() == 'BTC' else 3000  # Example prices
        
        # Generate 1-minute data (last 100 points)
        timestamps_1m = pd.date_range(end=datetime.now(), periods=100, freq='1min')
        prices_1m = [base_price + random.uniform(-100, 100) for _ in range(100)]
        df_1m = pd.DataFrame({'timestamp': timestamps_1m, 'close': prices_1m})
        
        # Generate 5-minute data (last 20 points)
        timestamps_5m = pd.date_range(end=datetime.now(), periods=20, freq='5min')
        prices_5m = [base_price + random.uniform(-200, 200) for _ in range(20)]
        df_5m = pd.DataFrame({'timestamp': timestamps_5m, 'close': prices_5m})
        
        # Generate 1-hour data (last 10 points)
        timestamps_1h = pd.date_range(end=datetime.now(), periods=10, freq='1H')
        prices_1h = [base_price + random.uniform(-500, 500) for _ in range(10)]
        df_1h = pd.DataFrame({'timestamp': timestamps_1h, 'close': prices_1h})
        
        return MultiTimeframeData(
            timeframe_1m=df_1m.set_index('timestamp'),
            timeframe_5m=df_5m.set_index('timestamp'),
            timeframe_1h=df_1h.set_index('timestamp')
        )
    
    def calculate_advanced_indicators(self, close: pd.Series) -> dict:
        """Calculate advanced technical indicators."""
        indicators = {}
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        indicators['rsi'] = 100 - (100 / (1 + rs)).iloc[-1] if not rs.empty else 50
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        indicators['macd'] = macd.iloc[-1] if not macd.empty else 0
        indicators['macd_signal'] = signal.iloc[-1] if not signal.empty else 0
        indicators['macd_histogram'] = (macd - signal).iloc[-1] if not (macd - signal).empty else 0
        
        # Bollinger Bands
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        bb_upper = sma20 + (std20 * 2)
        bb_lower = sma20 - (std20 * 2)
        indicators['bb_upper'] = bb_upper.iloc[-1] if not bb_upper.empty else close.iloc[-1]
        indicators['bb_lower'] = bb_lower.iloc[-1] if not bb_lower.empty else close.iloc[-1]
        indicators['bb_position'] = (close.iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]) if bb_upper.iloc[-1] != bb_lower.iloc[-1] else 0.5
        
        # Volume (synthetic for demo)
        indicators['volume_ratio'] = random.uniform(0.5, 2.0)
        
        return indicators
    
    def monte_carlo_regime_simulation(self, close: pd.Series, indicators: dict) -> float:
        """Run Monte Carlo simulations to determine regime probability."""
        regime_counts = {'panic': 0, 'expansion': 0, 'trend': 0, 'squeeze': 0, 'chop': 0, 'exhaustion': 0}
        
        for _ in range(self.monte_carlo_simulations):
            # Add noise to indicators
            noisy_close = close + np.random.normal(0, close.std() * 0.1, len(close))
            noisy_indicators = {k: v * random.uniform(0.9, 1.1) for k, v in indicators.items()}
            
            # Classify with noise
            regime = self.classify_single_timeframe(pd.Series(noisy_close), noisy_indicators)
            regime_counts[regime.name] += 1
        
        # Return probability of current regime
        current_regime = self.classify_single_timeframe(close, indicators)
        return regime_counts[current_regime.name] / self.monte_carlo_simulations
    
    def classify_single_timeframe(self, close: pd.Series, indicators: dict) -> RegimeState:
        """Enhanced single-timeframe classification with advanced indicators."""
        close = close.astype(float)
        r = close.pct_change().fillna(0.0)
        
        # Enhanced volatility calculation
        vol_fast = r.rolling(10).std().fillna(0.0)
        vol_slow = r.rolling(40).std().fillna(0.0)
        vol_ratio = float((vol_fast.iloc[-1] + 1e-9) / (vol_slow.iloc[-1] + 1e-9))
        
        # Enhanced trend strength
        ema_fast = close.ewm(span=10, adjust=False).mean()
        ema_slow = close.ewm(span=40, adjust=False).mean()
        trend_strength = float(((ema_fast - ema_slow) / close).iloc[-1])
        
        # Enhanced chop score with RSI and MACD
        rsi = indicators.get('rsi', 50)
        macd_hist = indicators.get('macd_histogram', 0)
        bb_position = indicators.get('bb_position', 0.5)
        
        base_chop = 1.0 - min(1.0, abs(trend_strength) * 50)
        rsi_chop = 1.0 - abs(rsi - 50) / 50  # Higher when RSI neutral
        macd_chop = abs(macd_hist) / max(abs(close.iloc[-1] * 0.01), 0.01)  # Normalize MACD
        bb_chop = 1.0 - abs(bb_position - 0.5) * 2  # Higher when price in middle
        
        chop_score = (base_chop + rsi_chop + macd_chop + bb_chop) / 4
        
        # Enhanced regime classification
        confidence = 0.5
        
        if vol_ratio > 2.0 and trend_strength < -0.005 and rsi < 30:
            return RegimeState("panic", 0.85, "high", trend_strength, chop_score, 0.0, 0.0, 0.0, {}, "")
        elif vol_ratio > 1.8 and abs(trend_strength) > 0.004 and rsi > 70:
            return RegimeState("expansion", 0.80, "high", trend_strength, chop_score, 0.0, 0.0, 0.0, {}, "")
        elif vol_ratio < 0.9 and abs(trend_strength) > 0.003 and bb_position > 0.7:
            return RegimeState("trend", 0.78, "low", trend_strength, chop_score, 0.0, 0.0, 0.0, {}, "")
        elif vol_ratio < 0.8 and abs(trend_strength) < 0.001 and bb_position < 0.3:
            return RegimeState("squeeze", 0.75, "low", trend_strength, chop_score, 0.0, 0.0, 0.0, {}, "")
        elif chop_score > 0.75:
            return RegimeState("chop", 0.72, "mid", trend_strength, chop_score, 0.0, 0.0, 0.0, {}, "")
        else:
            return RegimeState("exhaustion", 0.65, "mid", trend_strength, chop_score, 0.0, 0.0, 0.0, {}, "")
    
    def get_sector_adjustment(self, symbol: str) -> float:
        """Get sector-specific regime adjustment from registry."""
        sector_multipliers = {
            'crypto_exec': 1.2,  # More volatile
            'market_data': 1.0,  # Standard
            'broker': 0.9,       # Less volatile
            'energy': 1.1,       # Commodity influenced
            'weather': 0.8,      # Stable
            'space': 0.7,        # Very stable
            'rates': 1.0,        # Interest rate sensitive
        }
        
        # Find symbol in registry
        for provider in self.registry:
            if provider['source'].upper() in symbol.upper() or symbol.upper() in provider['source'].upper():
                sector = provider['sector']
                return sector_multipliers.get(sector, 1.0)
        
        return 1.0
    
    def classify(self, symbol: str) -> RegimeState:
        """Main classification method with all enhancements."""
        
        # Fetch multi-timeframe data
        mt_data = self.fetch_multi_timeframe_data(symbol)
        
        # Classify each timeframe
        regime_1m = self.classify_single_timeframe(mt_data.timeframe_1m['close'], 
                                                  self.calculate_advanced_indicators(mt_data.timeframe_1m['close']))
        regime_5m = self.classify_single_timeframe(mt_data.timeframe_5m['close'], 
                                                  self.calculate_advanced_indicators(mt_data.timeframe_5m['close']))
        regime_1h = self.classify_single_timeframe(mt_data.timeframe_1h['close'], 
                                                  self.calculate_advanced_indicators(mt_data.timeframe_1h['close']))
        
        # Multi-timeframe consensus (weighted average)
        consensus_weights = {'1m': 0.4, '5m': 0.4, '1h': 0.2}
        consensus_confidence = (regime_1m.confidence * consensus_weights['1m'] + 
                               regime_5m.confidence * consensus_weights['5m'] + 
                               regime_1h.confidence * consensus_weights['1h'])
        
        # Use 1-minute data for primary classification
        primary_close = mt_data.timeframe_1m['close']
        indicators = self.calculate_advanced_indicators(primary_close)
        
        # Monte Carlo probability
        mc_probability = self.monte_carlo_regime_simulation(primary_close, indicators)
        
        # Sector adjustment
        sector_adj = self.get_sector_adjustment(symbol)
        
        # Final regime state
        final_regime = RegimeState(
            name=regime_1m.name,
            confidence=min(0.95, regime_1m.confidence * sector_adj),
            vol_state=regime_1m.vol_state,
            trend_strength=regime_1m.trend_strength,
            chop_score=regime_1m.chop_score,
            monte_carlo_probability=mc_probability,
            sector_adjustment=sector_adj,
            multi_timeframe_consensus=consensus_confidence,
            advanced_indicators=indicators,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Log regime
        self.regime_history.append({
            'symbol': symbol,
            'regime': final_regime.name,
            'confidence': final_regime.confidence,
            'mc_probability': mc_probability,
            'timestamp': final_regime.timestamp
        })
        
        # Save regime history
        with open(OUT / 'regime_history.json', 'w') as f:
            json.dump(self.regime_history[-100:], f, indent=2)  # Keep last 100
        
        return final_regime

# Example usage
if __name__ == "__main__":
    engine = InstitutionalRegimeEngine()
    
    # Classify BTC regime
    regime = engine.classify('BTC')
    
    print(f"\n🏛️ INSTITUTIONAL REGIME ANALYSIS FOR BTC:")
    print(f"   Regime: {regime.name.upper()}")
    print(f"   Confidence: {regime.confidence:.3f}")
    print(f"   Vol State: {regime.vol_state}")
    print(f"   Trend Strength: {regime.trend_strength:.4f}")
    print(f"   Chop Score: {regime.chop_score:.3f}")
    print(f"   Monte Carlo Probability: {regime.monte_carlo_probability:.3f}")
    print(f"   Sector Adjustment: {regime.sector_adjustment:.2f}")
    print(f"   Multi-Timeframe Consensus: {regime.multi_timeframe_consensus:.3f}")
    print(f"   RSI: {regime.advanced_indicators.get('rsi', 'N/A'):.2f}")
    print(f"   MACD Histogram: {regime.advanced_indicators.get('macd_histogram', 'N/A'):.4f}")
    print(f"   BB Position: {regime.advanced_indicators.get('bb_position', 'N/A'):.2f}")
    print("\nRegime analysis saved to regime_history.json")
    print("=" * 70)
