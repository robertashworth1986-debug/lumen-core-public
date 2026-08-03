
from dataclasses import dataclass, field
from typing import List, Literal, Dict, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from scipy import stats
from sklearn.ensemble import RandomForestClassifier

Urgency = Literal["passive", "normal", "aggressive", "ultra_aggressive"]
Direction = Literal["long", "short", "flat"]

@dataclass
class GateInput:
    regime: str
    regime_confidence: float
    alignment_score: float
    liquidity_score: float
    signal_decay_score: float
    cross_confirm_score: float
    expected_edge_bps: float
    direction_hint: float = 0.5
    volatility_pct: float = 0.0
    correlation_to_portfolio: float = 0.0
    market_regime: str = "normal"  # normal, bull, bear, volatile
    sector_heat: float = 0.0
    historical_win_rate: float = 0.0
    monte_carlo_edge: float = 0.0
    live_data_freshness: float = 1.0  # 1.0 = fresh, 0.0 = stale
    # --- Orderbook/On-chain features ---
    orderbook_spread_bps: float = 0.0
    orderbook_depth_usd: float = 0.0
    orderbook_imbalance: float = 0.0
    onchain_tx_volume_usd: float = 0.0
    onchain_gas_fee_usd: float = 0.0
    onchain_whale_tx_count: int = 0
    onchain_block_height: int = 0
    onchain_data_freshness: float = 1.0  # 1.0 = fresh, 0.0 = stale
    # Add more as needed for future signals

@dataclass
class GateDecision:
    armed: bool
    direction: Direction
    urgency: Urgency
    reason_codes: List[str]
    composite_score: float
    confidence_level: float
    evolutionary_adaptation: Dict[str, float]
    monte_carlo_probability: float

class EvolutionarySignalGate:
    def evaluate_kpis(self, context=None):
        """
        Returns a dict of KPIs for MetaEngine allocation logic.
        KPIs: sharpe, max_drawdown, win_rate, total_decisions, avg_composite_score
        """
        stats = self.get_performance_stats() if hasattr(self, 'get_performance_stats') else {}
        # Fallbacks if stats are missing
        sharpe = stats.get('avg_composite_score', 0.0)
        win_rate = stats.get('win_rate', 0.0)
        total_decisions = stats.get('total_decisions', 0)
        max_drawdown = 0.0  # Placeholder, add real drawdown if tracked
        return {
            'sharpe': sharpe,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_decisions': total_decisions,
            'avg_composite_score': sharpe
        }
    def _determine_market_regime_multiplier(self, regime: str) -> float:
        """
        Returns a multiplier for thresholds based on market regime.
        """
        multipliers = {
            "bull": 0.9,      # More lenient in bull markets
            "bear": 1.1,      # Stricter in bear markets
            "volatile": 1.2,  # Much stricter in volatile markets
            "normal": 1.0     # Standard
        }
        return multipliers.get(regime, 1.0)
    """
    Ultra-robust institutional signal gate with evolutionary Monte Carlo edge detection.
    
    Features:
    - 12+ factor composite scoring (now includes orderbook and on-chain features)
    - Monte Carlo simulations on rolling live data
    - Machine learning adaptation of thresholds
    - Market regime-aware decision making
    - Sector correlation checks
    - Historical performance weighting
    - Live data freshness validation
    - Evolutionary threshold optimization
    - Orderbook/On-chain signal integration (spread, depth, imbalance, tx volume, gas, whale txs, block height, etc.)
    """
    
    def __init__(
        self,
        min_alignment: float = 0.55,
        min_regime_conf: float = 0.45,
        min_liquidity: float = 0.35,
        min_cross_confirm: float = 0.40,
        min_edge_bps: float = 5.0,
        min_composite_score: float = 0.60,
        max_volatility_pct: float = 8.0,
        max_correlation: float = 0.8,
        max_sector_heat: float = 0.35,
        min_orderbook_depth_usd: float = 10000.0,
        max_orderbook_spread_bps: float = 10.0,
        max_orderbook_imbalance: float = 0.5,
        min_onchain_tx_volume_usd: float = 100000.0,
        max_onchain_gas_fee_usd: float = 50.0,
        min_onchain_whale_tx_count: int = 1,
        monte_carlo_simulations: int = 2000,
        adaptation_window_days: int = 30,
        adaptation_enabled: bool = False,
        random_seed: int = 42,
    ):
        # Base thresholds (AGGRESSIVE MODE for faster compounding)
        self.base_thresholds = {
            "alignment": min_alignment,
            "regime_conf": min_regime_conf,
            "liquidity": min_liquidity,
            "cross_confirm": min_cross_confirm,
            "edge_bps": min_edge_bps,
            "volatility": max_volatility_pct,
            "correlation": max_correlation,
            "sector_heat": max_sector_heat,
            "signal_decay": 0.60,
            # --- Orderbook/On-chain thresholds ---
            "orderbook_depth_usd": min_orderbook_depth_usd,
            "orderbook_spread_bps": max_orderbook_spread_bps,
            "orderbook_imbalance": max_orderbook_imbalance,
            "onchain_tx_volume_usd": min_onchain_tx_volume_usd,
            "onchain_gas_fee_usd": max_onchain_gas_fee_usd,
            "onchain_whale_tx_count": min_onchain_whale_tx_count,
            "win_rate": 0.35,
            "monte_carlo": 0.45,
            "data_freshness": 0.70
        }
        self.min_composite_score = float(min_composite_score)
        
        # Evolutionary adaptation
        self.adaptation_window = timedelta(days=adaptation_window_days)
        self.decision_history: List[Dict] = []
        self.monte_carlo_sims = monte_carlo_simulations
        # Any adaptive thresholding is research-only until it is separately
        # preregistered and evaluated on a forward-held-out window.
        self.adaptation_enabled = bool(adaptation_enabled)
        self.random_seed = int(random_seed)
        
        # ML model for threshold adaptation
        self.ml_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.ml_trained = False
        
        # Rolling data for Monte Carlo
        self.price_history: Dict[str, pd.Series] = {}
        self.signal_history: List[Dict] = []
        
        # Evolutionary weights — rebalanced for live crypto scalping
        # Signal edge and momentum quality weighted highest; structural noise factors reduced
        self.factor_weights = {
            "alignment":    0.18,
            "regime_conf":  0.12,
            "liquidity":    0.12,
            "cross_confirm": 0.10,
            "edge_bps":     0.18,   # increased: core signal quality
            "volatility":   0.06,
            "correlation":  0.05,
            "sector_heat":  0.04,
            "signal_decay": 0.05,
            "win_rate":     0.05,   # increased: historical performance matters
            "monte_carlo":  0.03,   # increased slightly
            "data_freshness": 0.02
        }
    
    def _run_monte_carlo_simulation(self, input_data: GateInput, price_series: pd.Series) -> float:
        """
        Run Monte Carlo simulations to estimate edge probability.
        
        Simulates 1000+ scenarios of future price paths and signal performance.
        Returns probability of positive edge (0.0-1.0).
        """
        if len(price_series) < 100:
            return 0.5  # Neutral if insufficient data
        
        returns = price_series.pct_change().dropna()
        vol = returns.std()
        drift = returns.mean()
        
        positive_edge_count = 0
        rng = np.random.default_rng(self.random_seed)
        
        for _ in range(self.monte_carlo_sims):
            # Simulate future price path (next 20 periods)
            simulated_returns = rng.normal(drift, vol, 20)
            simulated_prices = price_series.iloc[-1] * np.cumprod(1 + simulated_returns)
            
            # Apply signal logic to simulated path
            signal_strength = input_data.expected_edge_bps / 10000  # Convert bps to decimal
            noise = rng.normal(0, vol * 0.5, 20)  # Add realistic noise
            
            simulated_signal = signal_strength + noise
            simulated_pnl = simulated_signal * simulated_returns
            
            if simulated_pnl.sum() > 0:
                positive_edge_count += 1
        
        return positive_edge_count / self.monte_carlo_sims
    
    def _adapt_thresholds_ml(self) -> Dict[str, float]:
        """
        Use machine learning to adapt thresholds based on historical performance.
        
        Trains on past decisions and their outcomes to optimize thresholds.
        """
        if not self.adaptation_enabled:
            return self.base_thresholds.copy()

        if len(self.decision_history) < 50:
            return self.base_thresholds  # Need more data
        
        # Prepare training data
        recent_decisions = []
        window_start = datetime.now(timezone.utc) - self.adaptation_window
        for decision in self.decision_history:
            try:
                observed_at = datetime.fromisoformat(str(decision["timestamp"]).replace("Z", "+00:00"))
                if observed_at.tzinfo is None:
                    observed_at = observed_at.replace(tzinfo=timezone.utc)
            except (KeyError, TypeError, ValueError):
                continue
            if observed_at > window_start:
                recent_decisions.append(decision)
        
        if len(recent_decisions) < 20:
            return self.base_thresholds
        
        # Features: input scores
        X = []
        # Target: was decision profitable? (1=yes, 0=no)
        y = []
        
        for decision in recent_decisions:
            features = [
                decision["inputs"]["alignment_score"],
                decision["inputs"]["regime_confidence"],
                decision["inputs"]["liquidity_score"],
                decision["inputs"]["cross_confirm_score"],
                decision["inputs"]["expected_edge_bps"],
                decision["inputs"]["volatility_pct"],
                decision["inputs"]["correlation_to_portfolio"],
                decision["inputs"]["sector_heat"],
                decision["inputs"]["signal_decay_score"],
                decision["inputs"]["historical_win_rate"],
                decision["inputs"]["monte_carlo_edge"],
                decision["inputs"]["live_data_freshness"]
            ]
            X.append(features)
            y.append(1 if decision.get("profitable", False) else 0)
        
        # Preserve temporal order. Random splitting time series can leak future
        # outcomes into the calibration window and inflate internal diagnostics.
        split_at = max(1, int(len(X) * 0.8))
        X_train, y_train = X[:split_at], y[:split_at]
        if len(X_train) < 16 or len(set(y_train)) < 2:
            return self.base_thresholds.copy()
        self.ml_model.fit(X_train, y_train)
        self.ml_trained = True
        
        # Use model to suggest threshold adjustments
        # (Simplified: adjust based on feature importance)
        importances = self.ml_model.feature_importances_
        
        adapted_thresholds = self.base_thresholds.copy()
        factor_names = list(self.factor_weights.keys())
        
        for i, factor in enumerate(factor_names):
            # Increase threshold for important factors, decrease for less important
            adjustment = (importances[i] - 0.08) * 0.1  # Small adjustments
            adapted_thresholds[factor] = max(0.1, min(1.0, adapted_thresholds[factor] + adjustment))
        
        return adapted_thresholds
    
    def _calculate_composite_score(self, x: GateInput, thresholds: Dict[str, float]) -> tuple:
        score = 1.0
        reason_codes = []
        # --- Existing features ---
        if x.alignment_score < thresholds["alignment"]:
            score -= 0.15
            reason_codes.append("low_alignment")
        if x.regime_confidence < thresholds["regime_conf"]:
            score -= 0.10
            reason_codes.append("low_regime_conf")
        if x.liquidity_score < thresholds["liquidity"]:
            score -= 0.10
            reason_codes.append("low_liquidity")
        if x.cross_confirm_score < thresholds["cross_confirm"]:
            score -= 0.10
            reason_codes.append("low_cross_confirm")
        if x.expected_edge_bps < thresholds["edge_bps"]:
            score -= 0.10
            reason_codes.append("low_edge")
        if x.volatility_pct > thresholds["volatility"]:
            score -= 0.10
            reason_codes.append("high_volatility")
        if abs(x.correlation_to_portfolio) > thresholds["correlation"]:
            score -= 0.05
            reason_codes.append("high_correlation")
        if x.sector_heat > thresholds["sector_heat"]:
            score -= 0.05
            reason_codes.append("sector_heat")
        if x.signal_decay_score > thresholds["signal_decay"]:
            score -= 0.05
            reason_codes.append("signal_decay")
        # --- Orderbook features ---
        if x.orderbook_depth_usd < thresholds["orderbook_depth_usd"]:
            score -= 0.10
            reason_codes.append("shallow_orderbook")
        if x.orderbook_spread_bps > thresholds["orderbook_spread_bps"]:
            score -= 0.10
            reason_codes.append("wide_spread")
        if abs(x.orderbook_imbalance) > thresholds["orderbook_imbalance"]:
            score -= 0.05
            reason_codes.append("orderbook_imbalance")
        # --- On-chain features ---
        if x.onchain_tx_volume_usd < thresholds["onchain_tx_volume_usd"]:
            score -= 0.05
            reason_codes.append("low_onchain_tx_volume")
        if x.onchain_gas_fee_usd > thresholds["onchain_gas_fee_usd"]:
            score -= 0.05
            reason_codes.append("high_gas_fee")
        if x.onchain_whale_tx_count < thresholds["onchain_whale_tx_count"]:
            score -= 0.05
            reason_codes.append("low_whale_activity")
        # Clamp score
        score = max(0.0, min(1.0, score))
        return score, reason_codes
        multipliers = {
            "bull": 0.9,      # More lenient in bull markets
            "bear": 1.1,      # Stricter in bear markets
            "volatile": 1.2,  # Much stricter in volatile markets
            "normal": 1.0     # Standard
        }
        return multipliers.get(regime, 1.0)
    
    def decide(self, x: GateInput, price_series: Optional[pd.Series] = None) -> GateDecision:
        """
        Make evolutionary gate decision with Monte Carlo edge detection.
        
        Args:
            x: GateInput with all factors
            price_series: Live price data for Monte Carlo simulations
        
        Returns:
            GateDecision with ultra-robust analysis
        """
        
        # Run Monte Carlo if we have price data
        monte_carlo_prob = self._run_monte_carlo_simulation(x, price_series) if price_series is not None else 0.5
        x.monte_carlo_edge = monte_carlo_prob
        
        # Adapt thresholds using ML
        adapted_thresholds = self._adapt_thresholds_ml()
        
        # Market regime adjustment
        regime_multiplier = self._determine_market_regime_multiplier(x.market_regime)
        
        # Apply regime adjustment to thresholds
        final_thresholds = {k: v * regime_multiplier for k, v in adapted_thresholds.items()}
        
        # Calculate composite score.
        # Backward-compatibility: older gate variants return (composite, reasons)
        # while newer variants return (composite, confidence, factors).
        composite_result = self._calculate_composite_score(x, final_thresholds)
        if isinstance(composite_result, tuple):
            if len(composite_result) >= 3:
                composite, confidence, factors = composite_result[0], composite_result[1], composite_result[2]
            elif len(composite_result) == 2:
                composite, factors = composite_result
                confidence = float(composite)
            elif len(composite_result) == 1:
                composite = composite_result[0]
                confidence = float(composite)
                factors = []
            else:
                composite = 0.0
                confidence = 0.0
                factors = []
        else:
            composite = float(composite_result)
            confidence = float(composite)
            factors = []
        
        # Check each factor against thresholds
        reasons = []
        factor_checks = {
            "alignment_too_low": x.alignment_score < final_thresholds["alignment"],
            "regime_conf_too_low": x.regime_confidence < final_thresholds["regime_conf"],
            "liquidity_too_low": x.liquidity_score < final_thresholds["liquidity"],
            "cross_confirm_too_low": x.cross_confirm_score < final_thresholds["cross_confirm"],
            "edge_too_small": x.expected_edge_bps < final_thresholds["edge_bps"],
            "volatility_too_high": x.volatility_pct > final_thresholds["volatility"],
            "correlation_too_high": abs(x.correlation_to_portfolio) > final_thresholds["correlation"],
            "sector_heat_too_high": x.sector_heat > final_thresholds["sector_heat"],
            "signal_stale": x.signal_decay_score > final_thresholds["signal_decay"],
            "win_rate_too_low": x.historical_win_rate < final_thresholds["win_rate"],
            "monte_carlo_edge_insufficient": x.monte_carlo_edge < final_thresholds["monte_carlo"],
            "data_stale": x.live_data_freshness < final_thresholds["data_freshness"]
        }
        
        for reason, failed in factor_checks.items():
            if failed:
                reasons.append(reason)

        for reason in (factors or []):
            if reason not in reasons:
                reasons.append(reason)
        
        # Decision logic
        armed = len(reasons) == 0 and composite >= float(self.min_composite_score)
        
        direction: Direction = "flat"
        urgency: Urgency = "passive"
        
        if armed:
            # Direction based on hint + Monte Carlo
            direction_hint = (x.direction_hint + monte_carlo_prob) / 2
            direction = "long" if direction_hint >= 0.5 else "short"
            
            # Urgency based on composite + edge
            if composite >= 0.82 and x.expected_edge_bps > 20:
                urgency = "ultra_aggressive"
            elif composite >= 0.72 or x.expected_edge_bps > 12:
                urgency = "aggressive"
            elif composite >= 0.65:
                urgency = "normal"
            else:
                urgency = "passive"
            
            # Reduce urgency in volatile markets
            if x.market_regime == "volatile":
                urgency_levels = ["passive", "normal", "aggressive", "ultra_aggressive"]
                current_idx = urgency_levels.index(urgency)
                urgency = urgency_levels[max(0, current_idx - 1)]
        
        # Evolutionary adaptation tracking
        adaptation = {
            "threshold_adjustments": {k: adapted_thresholds[k] - self.base_thresholds[k] for k in self.base_thresholds},
            "factor_weights": self.factor_weights.copy(),
            "regime_multiplier": regime_multiplier,
            "ml_model_trained": self.ml_trained
        }
        
        decision = GateDecision(
            armed=armed,
            direction=direction,
            urgency=urgency,
            reason_codes=reasons,
            composite_score=float(composite),
            confidence_level=float(confidence),
            evolutionary_adaptation=adaptation,
            monte_carlo_probability=float(monte_carlo_prob)
        )
        
        # Log decision for future adaptation
        self.decision_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                "alignment_score": x.alignment_score,
                "regime_confidence": x.regime_confidence,
                "liquidity_score": x.liquidity_score,
                "cross_confirm_score": x.cross_confirm_score,
                "expected_edge_bps": x.expected_edge_bps,
                "volatility_pct": x.volatility_pct,
                "correlation_to_portfolio": x.correlation_to_portfolio,
                "sector_heat": x.sector_heat,
                "signal_decay_score": x.signal_decay_score,
                "historical_win_rate": x.historical_win_rate,
                "monte_carlo_edge": x.monte_carlo_edge,
                "live_data_freshness": x.live_data_freshness
            },
            "decision": {
                "armed": armed,
                "direction": direction,
                "urgency": urgency,
                "composite_score": composite,
                "confidence": confidence
            },
            "profitable": None  # Will be updated later with P&L
        })
        
        # Keep only recent history
        cutoff = datetime.now(timezone.utc) - self.adaptation_window
        self.decision_history = [
            d for d in self.decision_history
            if datetime.fromisoformat(d["timestamp"]) > cutoff
        ]
        
        return decision
    
    def update_decision_outcome(self, timestamp: str, profitable: bool):
        """
        Update historical decision with outcome for ML training.
        """
        for decision in self.decision_history:
            if decision["timestamp"] == timestamp:
                decision["profitable"] = profitable
                break
    
    def get_performance_stats(self) -> Dict:
        """
        Get gate performance statistics for audit.
        """
        if not self.decision_history:
            return {}
        
        df = pd.DataFrame(self.decision_history)
        
        armed_decisions = df[df["decision"].apply(lambda x: x["armed"])]
        profitable_decisions = armed_decisions[armed_decisions["profitable"] == True]
        
        win_rate = len(profitable_decisions) / len(armed_decisions) if len(armed_decisions) > 0 else 0
        
        return {
            "total_decisions": len(df),
            "armed_rate": len(armed_decisions) / len(df),
            "win_rate": win_rate,
            "avg_composite_score": df["decision"].apply(lambda x: x["composite_score"]).mean(),
            "avg_confidence": df["decision"].apply(lambda x: x["confidence"]).mean(),
            "ml_model_trained": self.ml_trained
        }
    
    def export_audit_trail(self) -> str:
        """
        Export complete audit trail for institutional review.
        """
        return pd.DataFrame(self.decision_history).to_json(orient="records", indent=2)
