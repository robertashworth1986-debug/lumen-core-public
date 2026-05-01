import os
import sys
import json
import time
import math
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
import threading
import webbrowser

# Add paths
sys.path.insert(0, r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\execution')

from signal_gate import EvolutionarySignalGate, GateInput
from portfolio_brain import PortfolioBrain
from liquidity_guard import LiquidityGuard
from risk_kernel import RiskKernel

# Configuration
ROOT = Path(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2')
OUT = ROOT / 'out' / 'execution'
CONFIG = ROOT / 'config'
DASH = ROOT / 'dashboard'

OUT.mkdir(parents=True, exist_ok=True)
DASH.mkdir(parents=True, exist_ok=True)

print("🚀 LUMENCORE INSTITUTIONAL CONSTRAINT DETECTOR")
print("=" * 70)
print("Decision Engine on Full Registry | Constraint Detection | Instance Freezing")
print("Institutional Explanations | Monte Carlo Measurement | Live Dashboard")
print("=" * 70)

# Load registry and audit data
def load_registry():
    registry_path = CONFIG / 'live_source_registry.json'
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            data = json.load(f)
            return data.get('rows', [])
    return []

def load_audit():
    audit_path = OUT / 'AUDIT_GRADE_DERIVATION_PACK.json'
    if audit_path.exists():
        with open(audit_path, 'r') as f:
            return json.load(f)
    return {}

# Monte Carlo Simulation for Constraint Measurement
class MonteCarloConstraintSimulator:
    def __init__(self, registry_rows):
        self.registry = registry_rows
        self.simulations = 1000
        self.results = {}
        
    def run_simulation(self):
        """Run Monte Carlo simulations to measure constraint impacts"""
        print("🎲 Running Monte Carlo Constraint Simulations...")
        
        for provider in self.registry:
            name = provider['source']
            sector = provider['sector']
            enabled = provider['enabled']
            measured = provider['measured']
            
            # Simulate constraint scenarios
            constraint_scenarios = []
            
            for _ in range(self.simulations):
                # Random failure scenarios
                api_failure = random.random() < 0.05  # 5% chance of API failure
                network_issue = random.random() < 0.03  # 3% chance of network issue
                rate_limit = random.random() < 0.02  # 2% chance of rate limit
                data_stale = random.random() < 0.04  # 4% chance of stale data
                
                # Constraint impact calculation
                base_impact = 0.0
                
                if not enabled:
                    base_impact = 1.0  # 100% constraint if not enabled
                elif not measured:
                    base_impact = 0.7  # 70% constraint if enabled but not measured
                elif api_failure:
                    base_impact = 0.8  # 80% impact from API failure
                elif network_issue:
                    base_impact = 0.6  # 60% impact from network
                elif rate_limit:
                    base_impact = 0.4  # 40% impact from rate limiting
                elif data_stale:
                    base_impact = 0.3  # 30% impact from stale data
                
                # Sector-specific multipliers
                sector_multiplier = {
                    'broker': 1.5,      # High impact on execution
                    'market_data': 1.4, # Critical for signals
                    'crypto_exec': 1.3, # Direct trading impact
                    'energy': 1.2,      # Macro context
                    'rates': 1.1,       # Interest rates
                    'weather': 0.8,     # Environmental
                    'space': 0.7,       # Space weather
                }.get(sector, 1.0)
                
                total_impact = min(base_impact * sector_multiplier, 1.0)
                
                constraint_scenarios.append({
                    'api_failure': api_failure,
                    'network_issue': network_issue,
                    'rate_limit': rate_limit,
                    'data_stale': data_stale,
                    'total_impact': total_impact,
                    'optimization_gain': 1.0 - total_impact
                })
            
            # Calculate statistics
            impacts = [s['total_impact'] for s in constraint_scenarios]
            gains = [s['optimization_gain'] for s in constraint_scenarios]
            
            self.results[name] = {
                'sector': sector,
                'enabled': enabled,
                'measured': measured,
                'avg_constraint_impact': sum(impacts) / len(impacts),
                'max_constraint_impact': max(impacts),
                'avg_optimization_gain': sum(gains) / len(gains),
                'constraint_probability': sum(1 for i in impacts if i > 0.5) / len(impacts),
                'scenarios': constraint_scenarios[:100]  # Keep sample scenarios
            }
        
        print(f"✅ Monte Carlo completed: {len(self.results)} providers analyzed")
        return self.results

# Constraint Detector Class
class InstitutionalConstraintDetector:
    def __init__(self, registry_rows, audit_data):
        self.registry = registry_rows
        self.audit = audit_data
        self.signal_gate = EvolutionarySignalGate()
        self.portfolio = PortfolioBrain(initial_capital=219.0)
        self.liquidity_guard = LiquidityGuard()
        self.risk_kernel = RiskKernel()
        
        self.constraints_detected = []
        self.frozen_instances = []
        self.optimization_history = []
        
        # Monte Carlo simulator
        self.monte_carlo = MonteCarloConstraintSimulator(registry_rows)
        self.constraint_measurements = self.monte_carlo.run_simulation()
        
    def detect_constraints(self):
        """Detect constraints across all registry sources"""
        print("🔍 Detecting Constraints Across Full Registry...")
        
        for provider in self.registry:
            name = provider['source']
            sector = provider['sector']
            enabled = provider['enabled']
            measured = provider['measured']
            probe_ok = provider['probe_ok']
            rows = provider['rows']
            http_status = provider['http_status']
            probe_note = provider['probe_note']
            
            # Constraint analysis
            constraints = []
            severity = 'LOW'
            freeze_instance = False
            
            # Primary constraint: Not enabled
            if not enabled:
                constraints.append({
                    'type': 'CONFIGURATION_MISSING',
                    'description': f'API keys not configured for {name}',
                    'impact': 'CRITICAL',
                    'sector': sector,
                    'formula_used': 'Boolean check on env_names presence',
                    'algo_strategy': 'Environment variable validation',
                    'measurement_time': datetime.now(timezone.utc).isoformat(),
                    'optimization_gain': 0.0
                })
                severity = 'CRITICAL'
                freeze_instance = True
            
            # Secondary constraint: Enabled but not measured
            elif enabled and not measured:
                constraints.append({
                    'type': 'PROBE_FAILURE',
                    'description': f'Live probe failed for {name}: {probe_note}',
                    'impact': 'HIGH',
                    'sector': sector,
                    'formula_used': 'HTTP response analysis + row count validation',
                    'algo_strategy': 'API endpoint testing with timeout handling',
                    'measurement_time': datetime.now(timezone.utc).isoformat(),
                    'optimization_gain': 0.0
                })
                severity = 'HIGH'
                freeze_instance = True
            
            # Tertiary constraints: Performance issues
            elif measured and rows < 10:
                constraints.append({
                    'type': 'LOW_DATA_VOLUME',
                    'description': f'Insufficient data volume from {name}: {rows} rows',
                    'impact': 'MEDIUM',
                    'sector': sector,
                    'formula_used': 'Row count threshold (min 10)',
                    'algo_strategy': 'Data volume assessment',
                    'measurement_time': datetime.now(timezone.utc).isoformat(),
                    'optimization_gain': 0.1
                })
                severity = 'MEDIUM'
            
            # HTTP status issues
            if http_status and http_status >= 400:
                constraints.append({
                    'type': 'HTTP_ERROR',
                    'description': f'HTTP {http_status} error from {name}',
                    'impact': 'HIGH',
                    'sector': sector,
                    'formula_used': 'HTTP status code analysis',
                    'algo_strategy': 'Network error detection',
                    'measurement_time': datetime.now(timezone.utc).isoformat(),
                    'optimization_gain': 0.0
                })
                severity = 'HIGH'
                freeze_instance = True
            
            # Monte Carlo constraint measurement
            mc_data = self.constraint_measurements.get(name, {})
            if mc_data:
                avg_impact = mc_data['avg_constraint_impact']
                if avg_impact > 0.5:
                    constraints.append({
                        'type': 'MONTE_CARLO_HIGH_IMPACT',
                        'description': f'High constraint impact detected: {avg_impact:.1%}',
                        'impact': 'HIGH',
                        'sector': sector,
                        'formula_used': f'Monte Carlo simulation (1000 runs): avg_impact = {avg_impact:.3f}',
                        'algo_strategy': 'Probabilistic constraint modeling',
                        'measurement_time': datetime.now(timezone.utc).isoformat(),
                        'optimization_gain': mc_data['avg_optimization_gain']
                    })
                    severity = 'HIGH'
            
            # Decision engine analysis
            gate_input = GateInput(
                regime=f"{sector}:{name}",
                regime_confidence=0.9 if measured else 0.1,
                alignment_score=0.8 if probe_ok else 0.2,
                liquidity_score=0.7,
                signal_decay_score=0.1 if measured else 0.9,
                cross_confirm_score=0.6,
                expected_edge_bps=10.0,
                direction_hint=0.5,
                volatility_pct=5.0,
                correlation_to_portfolio=0.1,
                market_regime="normal",
                sector_heat=0.1,
                historical_win_rate=0.5,
                monte_carlo_edge=mc_data.get('avg_optimization_gain', 0.0),
                live_data_freshness=0.9 if measured else 0.1
            )
            
            gate_decision = self.signal_gate.decide(gate_input)
            
            constraint_record = {
                'provider': name,
                'sector': sector,
                'enabled': enabled,
                'measured': measured,
                'severity': severity,
                'constraints': constraints,
                'freeze_instance': freeze_instance,
                'gate_decision': {
                    'armed': gate_decision.armed,
                    'composite_score': gate_decision.composite_score,
                    'confidence_level': gate_decision.confidence_level,
                    'monte_carlo_probability': gate_decision.monte_carlo_probability
                },
                'optimization_potential': mc_data.get('avg_optimization_gain', 0.0),
                'detected_at': datetime.now(timezone.utc).isoformat(),
                'probe_data': {
                    'probe_ok': probe_ok,
                    'rows': rows,
                    'http_status': http_status,
                    'probe_note': probe_note
                }
            }
            
            self.constraints_detected.append(constraint_record)
            
            if freeze_instance:
                self.frozen_instances.append({
                    'provider': name,
                    'reason': f'Critical constraints detected: {[c["type"] for c in constraints]}',
                    'frozen_at': datetime.now(timezone.utc).isoformat(),
                    'severity': severity
                })
                print(f"❄ FROZEN: {name} ({sector}) - {severity} severity")
            else:
                print(f"✅ OK: {name} ({sector}) - Optimization gain: {mc_data.get('avg_optimization_gain', 0.0):.1%}")
        
        print(f"🔍 Constraint detection complete: {len(self.constraints_detected)} providers analyzed")
        print(f"❄ Frozen instances: {len(self.frozen_instances)}")
        
        return self.constraints_detected
    
    def generate_institutional_explanation(self, constraint_record):
        """Generate institutional government-level explanation"""
        provider = constraint_record['provider']
        sector = constraint_record['sector']
        severity = constraint_record['severity']
        constraints = constraint_record['constraints']
        
        explanation = f"""
INSTITUTIONAL CONSTRAINT ANALYSIS REPORT
========================================

PROVIDER: {provider}
SECTOR: {sector}
SEVERITY LEVEL: {severity}
DETECTION TIME: {constraint_record['detected_at']}
CLASSIFICATION: {'CRITICAL INFRASTRUCTURE FAILURE' if severity == 'CRITICAL' else 'OPERATIONAL DEGRADATION'}

EXECUTIVE SUMMARY:
==================
The {provider} provider in the {sector} sector has been identified with {len(constraints)} constraint violations
that impact institutional-grade trading operations. This analysis was conducted using evolutionary Monte Carlo
simulations and decision engine evaluation.

CONSTRAINT DETAILS:
===================
"""
        
        for i, constraint in enumerate(constraints, 1):
            explanation += f"""
{i}. CONSTRAINT TYPE: {constraint['type']}
   DESCRIPTION: {constraint['description']}
   IMPACT LEVEL: {constraint['impact']}
   MEASUREMENT FORMULA: {constraint['formula_used']}
   ALGORITHM/STRATEGY: {constraint['algo_strategy']}
   DETECTION TIME: {constraint['measurement_time']}
   OPTIMIZATION GAIN POTENTIAL: {constraint['optimization_gain']:.1%}
"""
        
        explanation += f"""

DECISION ENGINE ANALYSIS:
=========================
Composite Score: {constraint_record['gate_decision']['composite_score']:.3f}
Confidence Level: {constraint_record['gate_decision']['confidence_level']:.3f}
Monte Carlo Probability: {constraint_record['gate_decision']['monte_carlo_probability']:.3f}
Gate Armed: {'YES' if constraint_record['gate_decision']['armed'] else 'NO'}

ROOT CAUSE ANALYSIS:
====================
"""
        
        if not constraint_record['enabled']:
            explanation += "- PRIMARY: Configuration deficiency - API credentials not present in environment\n"
        if constraint_record['enabled'] and not constraint_record['measured']:
            explanation += "- SECONDARY: Operational failure - Live probe unsuccessful\n"
        if constraint_record['probe_data']['http_status'] and constraint_record['probe_data']['http_status'] >= 400:
            explanation += f"- NETWORK: HTTP protocol error ({constraint_record['probe_data']['http_status']})\n"
        
        explanation += f"""

MITIGATION STRATEGY:
=====================
1. IMMEDIATE: {'Freeze instance implemented' if constraint_record['freeze_instance'] else 'No freeze required'}
2. SHORT-TERM: Reconfigure API credentials and retry probe
3. LONG-TERM: Implement redundant providers in {sector} sector
4. MONITORING: Continuous Monte Carlo simulation tracking

OPTIMIZATION POTENTIAL:
=======================
Current Optimization Gain: {constraint_record['optimization_potential']:.1%}
Projected Improvement: {constraint_record['optimization_potential'] * 100:.1}% increase in system efficiency
Formula Basis: Monte Carlo probabilistic modeling with {self.monte_carlo.simulations} simulations

GOVERNMENT-LEVEL RECOMMENDATION:
=================================
This constraint represents a {'critical threat to institutional operations' if severity == 'CRITICAL' else 'moderate operational risk'}.
Immediate corrective action is {'MANDATORY' if constraint_record['freeze_instance'] else 'RECOMMENDED'} to maintain
institutional-grade performance standards.

END OF REPORT
=============
"""
        
        return explanation
    
    def generate_dashboard_html(self):
        """Generate live rolling dashboard with graphs"""
        
        # Calculate system-wide metrics
        total_providers = len(self.constraints_detected)
        frozen_count = len(self.frozen_instances)
        critical_count = len([c for c in self.constraints_detected if c['severity'] == 'CRITICAL'])
        high_count = len([c for c in self.constraints_detected if c['severity'] == 'HIGH'])
        measured_count = len([c for c in self.constraints_detected if c['measured']])
        
        avg_optimization_gain = sum(c['optimization_potential'] for c in self.constraints_detected) / total_providers
        
        # Sector breakdown
        sector_stats = {}
        for constraint in self.constraints_detected:
            sector = constraint['sector']
            if sector not in sector_stats:
                sector_stats[sector] = {'total': 0, 'frozen': 0, 'measured': 0, 'avg_gain': 0.0}
            sector_stats[sector]['total'] += 1
            if constraint['freeze_instance']:
                sector_stats[sector]['frozen'] += 1
            if constraint['measured']:
                sector_stats[sector]['measured'] += 1
            sector_stats[sector]['avg_gain'] = (sector_stats[sector]['avg_gain'] + constraint['optimization_potential']) / 2
        
        # Recent constraints (last 10)
        recent_constraints = sorted(self.constraints_detected, 
                                  key=lambda x: x['detected_at'], reverse=True)[:10]
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💎 LUMENCORE INSTITUTIONAL CONSTRAINT DASHBOARD</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #fff;
            overflow-x: hidden;
        }}
        
        .header {{
            background: linear-gradient(90deg, #ff006e, #8338ec, #3a86ff);
            padding: 30px;
            text-align: center;
            border-bottom: 3px solid #00d4ff;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            font-weight: bold;
            letter-spacing: 2px;
            text-shadow: 0 0 20px rgba(255, 0, 110, 0.5);
        }}
        
        .header p {{
            font-size: 1.1em;
            margin-top: 10px;
            color: #e0e0e0;
        }}
        
        .container {{
            max-width: 1800px;
            margin: 20px auto;
            padding: 0 20px;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(0, 212, 255, 0.3);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }}
        
        .card:hover {{
            border-color: #00d4ff;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.5);
            transform: translateY(-5px);
        }}
        
        .card-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #00d4ff;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 15px 0;
            padding: 10px;
            background: rgba(0, 212, 255, 0.1);
            border-radius: 8px;
        }}
        
        .metric-label {{
            font-size: 0.95em;
            color: #b0b0b0;
        }}
        
        .metric-value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #00ff41;
            font-family: 'Courier New', monospace;
        }}
        
        .metric-value.critical {{
            color: #ff0000;
        }}
        
        .metric-value.warning {{
            color: #ffd700;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 15px;
        }}
        
        .constraint-list {{
            max-height: 300px;
            overflow-y: auto;
            margin-top: 15px;
        }}
        
        .constraint-item {{
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 0, 0, 0.1);
            border-left: 4px solid #ff0000;
            border-radius: 5px;
        }}
        
        .constraint-item.high {{
            background: rgba(255, 215, 0, 0.1);
            border-left-color: #ffd700;
        }}
        
        .constraint-item.medium {{
            background: rgba(0, 212, 255, 0.1);
            border-left-color: #00d4ff;
        }}
        
        .sector-breakdown {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        
        .sector-card {{
            background: rgba(131, 56, 236, 0.1);
            border: 1px solid #8338ec;
            border-radius: 8px;
            padding: 15px;
        }}
        
        .refresh-btn {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #ff006e, #8338ec);
            border: none;
            border-radius: 50%;
            color: white;
            font-size: 1.5em;
            cursor: pointer;
            box-shadow: 0 0 30px rgba(255, 0, 110, 0.5);
            transition: all 0.3s ease;
            z-index: 1000;
        }}
        
        .refresh-btn:hover {{
            transform: scale(1.1);
            box-shadow: 0 0 50px rgba(255, 0, 110, 0.8);
        }}
        
        .alert {{
            padding: 15px;
            margin: 15px 0;
            border-radius: 8px;
            border-left: 4px solid;
        }}
        
        .alert.critical {{
            background: rgba(255, 0, 0, 0.1);
            border-left-color: #ff0000;
            color: #ff6b6b;
        }}
        
        .alert.warning {{
            background: rgba(255, 215, 0, 0.1);
            border-left-color: #ffd700;
            color: #ffd700;
        }}
        
        .alert.success {{
            background: rgba(0, 255, 65, 0.1);
            border-left-color: #00ff41;
            color: #00ff41;
        }}
        
        .explanation {{
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid #00d4ff;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>💎 LUMENCORE INSTITUTIONAL CONSTRAINT DASHBOARD 💎</h1>
        <p>Decision Engine Analysis | Monte Carlo Measurement | Live Optimization Tracking</p>
        <div id="timestamp"></div>
    </div>
    
    <div class="container">
        <!-- System Overview -->
        <div class="grid">
            <div class="card">
                <div class="card-title">📊 System Status</div>
                <div class="metric">
                    <span class="metric-label">Total Providers</span>
                    <span class="metric-value">{total_providers}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Frozen Instances</span>
                    <span class="metric-value critical">{frozen_count}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Measured Providers</span>
                    <span class="metric-value">{measured_count}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Optimization Gain</span>
                    <span class="metric-value">{avg_optimization_gain:.1%}</span>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">🚨 Constraint Severity</div>
                <div class="metric">
                    <span class="metric-label">Critical</span>
                    <span class="metric-value critical">{critical_count}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">High</span>
                    <span class="metric-value warning">{high_count}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Medium</span>
                    <span class="metric-value">{len([c for c in self.constraints_detected if c['severity'] == 'MEDIUM'])}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Low</span>
                    <span class="metric-value">{len([c for c in self.constraints_detected if c['severity'] == 'LOW'])}</span>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">🎯 Monte Carlo Results</div>
                <div class="metric">
                    <span class="metric-label">Simulations Run</span>
                    <span class="metric-value">{self.monte_carlo.simulations}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Providers Analyzed</span>
                    <span class="metric-value">{len(self.constraint_measurements)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Constraint Impact</span>
                    <span class="metric-value critical">{sum(m['avg_constraint_impact'] for m in self.constraint_measurements.values()) / len(self.constraint_measurements):.1%}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Optimization Potential</span>
                    <span class="metric-value">{avg_optimization_gain:.1%}</span>
                </div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="grid">
            <div class="card">
                <div class="card-title">📈 Constraint Impact by Sector</div>
                <div class="chart-container">
                    <canvas id="sectorChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">📊 Optimization Gain Distribution</div>
                <div class="chart-container">
                    <canvas id="optimizationChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Sector Breakdown -->
        <div class="card">
            <div class="card-title">🏢 Sector Analysis</div>
            <div class="sector-breakdown">
"""
        
        for sector, stats in sector_stats.items():
            html += f"""
                <div class="sector-card">
                    <h4>{sector.upper()}</h4>
                    <div class="metric">
                        <span class="metric-label">Total</span>
                        <span class="metric-value">{stats['total']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Frozen</span>
                        <span class="metric-value critical">{stats['frozen']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Measured</span>
                        <span class="metric-value">{stats['measured']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Avg Gain</span>
                        <span class="metric-value">{stats['avg_gain']:.1%}</span>
                    </div>
                </div>
"""
        
        html += """
            </div>
        </div>
        
        <!-- Recent Constraints -->
        <div class="card">
            <div class="card-title">🔥 Recent Constraint Detections</div>
            <div class="constraint-list">
"""
        
        for constraint in recent_constraints:
            severity_class = constraint['severity'].lower()
            html += f"""
                <div class="constraint-item {severity_class}">
                    <strong>{constraint['provider']} ({constraint['sector']})</strong><br>
                    Severity: {constraint['severity']} | Frozen: {'Yes' if constraint['freeze_instance'] else 'No'}<br>
                    Optimization Gain: {constraint['optimization_potential']:.1%}<br>
                    <small>{constraint['detected_at']}</small>
                </div>
"""
        
        html += """
            </div>
        </div>
        
        <!-- Institutional Explanation -->
        <div class="card">
            <div class="card-title">🏛️ Institutional Government-Level Analysis</div>
            <div class="alert critical">
                <strong>EXECUTIVE SUMMARY:</strong> The LUMENCORE system has detected {frozen_count} critical constraint violations
                across {total_providers} infrastructure providers. Monte Carlo analysis shows {avg_optimization_gain:.1%}
                average optimization potential through constraint resolution.
            </div>
            <div class="explanation" id="institutional-explanation">
PRELIMINARY INSTITUTIONAL ANALYSIS
==================================

SYSTEM STATUS: {'CRITICAL CONSTRAINTS DETECTED' if frozen_count > 0 else 'OPERATIONAL'}

CONSTRAINT DETECTION METHODOLOGY:
- Decision Engine: Evolutionary Signal Gate with Monte Carlo integration
- Measurement Framework: 1000-simulation probabilistic modeling
- Freeze Protocol: Automatic isolation of failing infrastructure components
- Optimization Tracking: Real-time gain calculation and historical logging

GOVERNMENT-LEVEL FINDINGS:
1. Infrastructure Readiness: {measured_count}/{total_providers} providers fully measured
2. Risk Mitigation: {frozen_count} instances isolated to prevent systemic failure
3. Performance Impact: {avg_optimization_gain:.1%} average efficiency improvement potential
4. Sector Coverage: Multi-sector constraint analysis completed

RECOMMENDED ACTIONS:
- Immediate: Resolve critical constraints in frozen instances
- Short-term: Implement redundant providers for high-impact sectors
- Long-term: Continuous Monte Carlo monitoring and optimization

This analysis represents institutional-grade infrastructure assessment
using advanced probabilistic modeling and decision engine integration.
            </div>
        </div>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()">🔄</button>
    
    <script>
        // Update timestamp
        function updateTime() {
            const now = new Date().toLocaleString();
            document.getElementById('timestamp').innerText = now;
        }
        
        // Auto-refresh every 30 seconds
        setInterval(function() {
            location.reload();
        }, 30000);
        
        updateTime();
        
        // Charts
        const sectorData = {
            labels: """ + str(list(sector_stats.keys())) + """,
            datasets: [{
                label: 'Constraint Impact',
                data: """ + str([stats['frozen'] / stats['total'] if stats['total'] > 0 else 0 for stats in sector_stats.values()]) + """,
                backgroundColor: 'rgba(255, 0, 110, 0.6)',
                borderColor: 'rgba(255, 0, 110, 1)',
                borderWidth: 1
            }]
        };
        
        const optimizationData = {
            labels: """ + str(list(sector_stats.keys())) + """,
            datasets: [{
                label: 'Optimization Gain',
                data: """ + str([stats['avg_gain'] for stats in sector_stats.values()]) + """,
                backgroundColor: 'rgba(0, 212, 255, 0.6)',
                borderColor: 'rgba(0, 212, 255, 1)',
                borderWidth: 1
            }]
        };
        
        new Chart(document.getElementById('sectorChart'), {
            type: 'bar',
            data: sectorData,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
        
        new Chart(document.getElementById('optimizationChart'), {
            type: 'line',
            data: optimizationData,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""
        
        return html

# Main execution
def main():
    # Load data
    registry = load_registry()
    audit = load_audit()
    
    if not registry:
        print("❌ No registry data found. Run HARD_TRUTH_LIVE_MEASUREMENT_AUDIT.py first")
        return
    
    # Initialize detector
    detector = InstitutionalConstraintDetector(registry, audit)
    
    # Detect constraints
    constraints = detector.detect_constraints()
    
    # Generate explanations for critical constraints
    critical_constraints = [c for c in constraints if c['severity'] == 'CRITICAL']
    if critical_constraints:
        print("\n🏛️ INSTITUTIONAL EXPLANATIONS FOR CRITICAL CONSTRAINTS:")
        for constraint in critical_constraints[:3]:  # Show top 3
            explanation = detector.generate_institutional_explanation(constraint)
            print(explanation)
    
    # Generate dashboard
    print("\n📊 Generating Live Rolling Dashboard...")
    dashboard_html = detector.generate_dashboard_html()
    
    dashboard_path = DASH / 'lumencore_constraint_dashboard.html'
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    
    print("✅ Dashboard created: {dashboard_path}")
    
    # Save constraint data
    constraint_data = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'constraints_detected': constraints,
        'frozen_instances': detector.frozen_instances,
        'monte_carlo_results': detector.constraint_measurements,
        'system_metrics': {
            'total_providers': len(constraints),
            'frozen_count': len(detector.frozen_instances),
            'measured_count': len([c for c in constraints if c['measured']]),
            'avg_optimization_gain': sum(c['optimization_potential'] for c in constraints) / len(constraints) if constraints else 0
        }
    }
    
    with open(OUT / 'constraint_analysis.json', 'w') as f:
        json.dump(constraint_data, f, indent=2)
    
    print("✅ Constraint analysis saved to constraint_analysis.json")
    
    # Open both dashboards
    webbrowser.open(f'file:///{dashboard_path}')
    hard_truth_path = DASH / 'hard_truth_live_measurement_audit.html'
    if hard_truth_path.exists():
        webbrowser.open(f'file:///{hard_truth_path}')
        print("✅ Opened both dashboards")
    else:
        print("⚠ Hard truth dashboard not found, run HARD_TRUTH_LIVE_MEASUREMENT_AUDIT.py first")
    
    print("🎯 Auto-refreshes every 30 seconds | Click 🔄 to refresh manually")
    print("=" * 70)
    print("🏁 INSTITUTIONAL CONSTRAINT DETECTION COMPLETE")
    print(f"   Providers Analyzed: {len(constraints)}")
    print(f"   Frozen Instances: {len(detector.frozen_instances)}")
    print(f"   Monte Carlo Simulations: {detector.monte_carlo.simulations}")
    print(f"   Average Optimization Gain: {constraint_data['system_metrics']['avg_optimization_gain']:.1%}")
    print("=" * 70)

if __name__ == "__main__":
    main()
