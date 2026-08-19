import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
import time

# Configuration
ROOT = Path(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2')
OUT = ROOT / 'out' / 'execution'
DASH = ROOT / 'dashboard'
TOP_STRATEGY_BASELINE = OUT / 'top_system_strategy_baseline.json'
INSTITUTIONAL_SUMMARY_FILE = OUT / 'institutional_summary.json'
ROLLING_PERFORMANCE_FILE = ROOT / 'out' / 'rolling_performance.json'
CHAIN_FILE = ROOT / 'out' / 'unified_dashboard_chain_of_custody_sha256.json'
GRANT_PROPOSALS_FILE = ROOT / 'out' / 'institutional_grant_proposals.json'

def load_json_safe(filepath):
    """Safely load JSON files"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def get_current_metrics():
    """Get current trading metrics"""
    portfolio = load_json_safe(OUT / 'portfolio_summary.json')
    trades = load_json_safe(OUT / 'trade_log.json')
    pyramid_status = load_json_safe(OUT / 'pyramid_milestone_status.json')
    signal_audit = load_json_safe(OUT / 'signal_gate_audit.json')
    risk_status = load_json_safe(OUT / 'risk_status.json')
    kraken_balance = load_json_safe(OUT / 'kraken_balance.json')
    baseline = load_json_safe(TOP_STRATEGY_BASELINE)
    grant_proposals = load_json_safe(GRANT_PROPOSALS_FILE)
    institutional_summary = load_json_safe(INSTITUTIONAL_SUMMARY_FILE)
    rolling_performance = load_json_safe(ROLLING_PERFORMANCE_FILE)
    chain_data = load_json_safe(CHAIN_FILE)

    return {
        'portfolio': portfolio,
        'trades': trades if isinstance(trades, list) else [],
        'pyramid': pyramid_status,
        'signal_gate': signal_audit,
        'risk': risk_status,
        'balance': kraken_balance,
        'baseline': baseline if isinstance(baseline, dict) else {},
        'grant_proposals': grant_proposals if isinstance(grant_proposals, dict) else {},
        'institutional_summary': institutional_summary if isinstance(institutional_summary, dict) else {},
        'rolling': rolling_performance if isinstance(rolling_performance, dict) else {},
        'chain': chain_data if isinstance(chain_data, dict) else {},
    }

def generate_dashboard_html():
    """Generate complete institutional-grade dashboard"""
    
    metrics = get_current_metrics()
    
    portfolio = metrics['portfolio']
    trades = metrics['trades']
    pyramid = metrics['pyramid']
    signal_gate = metrics['signal_gate']
    risk = metrics['risk']
    balance = metrics['balance']
    baseline = metrics.get('baseline', {}) or {}
    grant_proposals = metrics.get('grant_proposals', {}) or {}
    institutional_summary = metrics.get('institutional_summary', {}) or {}
    rolling = metrics.get('rolling', {}) or {}
    chain = metrics.get('chain', {}) or {}
    
    top_baseline = baseline.get('baseline', {}) if isinstance(baseline.get('baseline', {}), dict) else {}
    grant_items = grant_proposals.get('grant_proposals', []) if isinstance(grant_proposals.get('grant_proposals', []), list) else []
    alignments = baseline.get('grant_evidence', {}).get('project_alignment', []) if isinstance(baseline.get('grant_evidence', {}).get('project_alignment', []), list) else []
    proof_count = len(baseline.get('grant_evidence', {}).get('proof_files', []) if isinstance(baseline.get('grant_evidence', {}).get('proof_files', []), list) else [])
    chain_files = chain.get('files', []) if isinstance(chain.get('files', []), list) else []
    proof_chain_count = len(chain_files)
    proof_chain_latest = chain_files[-1]['path'] if proof_chain_count else 'No proof chain'
    proof_chain_latest_name = Path(str(proof_chain_latest)).name
    optimization_gain_pct = float(top_baseline.get('top_test_vs_baseline', 0.0)) * 100.0
    optimization_label = f"{optimization_gain_pct:.1f}% improvement vs baseline"
    optimization_status = 'EXCEEDS 90% TARGET' if optimization_gain_pct >= 90.0 else 'TARGET IN PROGRESS'
    recent_txids = [t.get('txid', 'N/A') for t in trades[-3:]] if trades else []
    master_badge_state = 'ACTIVE' if optimization_gain_pct >= 90.0 else 'BUILDING'
    
    # Extract key metrics
    current_equity = portfolio.get('current_equity', 219.0) if portfolio else 219.0
    rolling_equity = rolling.get('current_equity', current_equity)
    rolling_live = rolling.get('live_now', False)
    rolling_points = rolling.get('equity_curve_points', 0)
    realized_pnl = portfolio.get('realized_pnl_total', 0.0) if portfolio else 0.0
    unrealized_pnl = portfolio.get('unrealized_pnl_total', 0.0) if portfolio else 0.0
    win_rate = portfolio.get('win_rate', 0.0) if portfolio else 0.0
    total_trades = portfolio.get('total_trades', 0) if portfolio else 0
    max_drawdown = portfolio.get('max_drawdown', 0.0) if portfolio else 0.0
    sharpe_ratio = portfolio.get('sharpe_ratio', 0.0) if portfolio else 0.0
    
    pyramid_level = pyramid.get('CurrentLevel', 1) if pyramid else 1
    
    open_positions = len(trades) if trades else 0
    
    # Calculate trade stats
    winning_trades = len([t for t in trades if t.get('pnl', 0) > 0]) if trades else 0
    losing_trades = len([t for t in trades if t.get('pnl', 0) < 0]) if trades else 0
    total_pnl = sum([t.get('pnl', 0) for t in trades]) if trades else 0
    avg_win = total_pnl / winning_trades if winning_trades > 0 else 0
    
    # Color coding
    def get_color(value, threshold_low=0, threshold_high=100):
        if value >= threshold_high:
            return '#00FF41'  # Green
        elif value >= threshold_low:
            return '#FFD700'  # Yellow
        else:
            return '#FF0000'  # Red
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎯 LUMENCORE INSTITUTIONAL DASHBOARD</title>
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
            
            .timestamp {{
                position: absolute;
                top: 10px;
                right: 20px;
                font-size: 0.9em;
                color: #00d4ff;
            }}
            
            .container {{
                max-width: 1600px;
                margin: 20px auto;
                padding: 0 20px;
            }}
            
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
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
            
            .metric-value.negative {{
                color: #ff0000;
            }}
            
            .metric-value.neutral {{
                color: #ffd700;
            }}
            .metric-value.badge {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background: rgba(0, 255, 65, 0.15);
                color: #00ff41;
                padding: 6px 10px;
                border-radius: 999px;
                font-size: 0.95em;
                font-weight: 700;
                letter-spacing: 0.04em;
            }}
            
            .status-indicator {{
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }}
            
            .status-indicator.active {{
                background: #00ff41;
            }}
            
            .status-indicator.warning {{
                background: #ffd700;
            }}
            
            .status-indicator.inactive {{
                background: #ff0000;
            }}
            
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
            
            .pyramid {{
                background: linear-gradient(135deg, rgba(51, 134, 236, 0.2), rgba(255, 0, 110, 0.2));
                border: 2px solid #8338ec;
                border-radius: 15px;
                padding: 20px;
                margin-top: 20px;
            }}
            
            .pyramid-level {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                margin: 8px 0;
                background: rgba(131, 56, 236, 0.1);
                border-left: 4px solid #8338ec;
                border-radius: 8px;
            }}
            
            .pyramid-level.active {{
                background: rgba(0, 255, 65, 0.1);
                border-left: 4px solid #00ff41;
            }}
            
            .trades-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 8px;
                overflow: hidden;
            }}
            
            .trades-table th {{
                background: rgba(0, 212, 255, 0.2);
                padding: 12px;
                text-align: left;
                font-weight: bold;
                color: #00d4ff;
                border-bottom: 2px solid #00d4ff;
            }}
            
            .trades-table td {{
                padding: 10px 12px;
                border-bottom: 1px solid rgba(0, 212, 255, 0.1);
            }}
            
            .trades-table tr:hover {{
                background: rgba(0, 212, 255, 0.1);
            }}
            
            .txid {{
                font-family: 'Courier New', monospace;
                font-size: 0.85em;
                color: #00d4ff;
                word-break: break-all;
            }}
            
            .chart-container {{
                position: relative;
                height: 300px;
                margin-top: 20px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 8px;
                padding: 15px;
            }}
            
            .grid-2 {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 20px;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                color: #666;
                border-top: 1px solid rgba(0, 212, 255, 0.2);
            }}
            
            .alert {{
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid;
            }}
            
            .alert.danger {{
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
            
            .refresh-btn.spinning {{
                animation: spin 2s linear infinite;
            }}
            
            @keyframes spin {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>💎 LUMENCORE INSTITUTIONAL DASHBOARD 💎</h1>
            <p>Evolutionary Monte Carlo Edge Detection | Real-Time Execution</p>
            <div class="timestamp" id="timestamp"></div>
        </div>
        
        <div class="container">
            <!-- Key Metrics -->
            <div class="grid">
                <div class="card">
                    <div class="card-title">
                        <span class="status-indicator active"></span>Portfolio Status
                    </div>
                    <div class="metric">
                        <span class="metric-label">Current Equity</span>
                        <span class="metric-value">${current_equity:.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Realized P&L</span>
                        <span class="metric-value {('negative' if realized_pnl < 0 else '')}">${realized_pnl:.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Unrealized P&L</span>
                        <span class="metric-value {('negative' if unrealized_pnl < 0 else '')}">${unrealized_pnl:.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Total P&L</span>
                        <span class="metric-value {('negative' if (realized_pnl + unrealized_pnl) < 0 else '')}">${(realized_pnl + unrealized_pnl):.2f}</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">
                        <span class="status-indicator {('warning' if max_drawdown > 5 else 'active')}"></span>Performance Metrics
                    </div>
                    <div class="metric">
                        <span class="metric-label">Win Rate</span>
                        <span class="metric-value">{win_rate:.2%}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Sharpe Ratio</span>
                        <span class="metric-value {('neutral' if sharpe_ratio < 1.0 else '')}">{sharpe_ratio:.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Max Drawdown</span>
                        <span class="metric-value {('negative' if max_drawdown > 5 else '')}">{max_drawdown:.2%}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Total Trades</span>
                        <span class="metric-value">{total_trades}</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">
                        <span class="status-indicator active"></span>Top System Baseline
                    </div>
                    <div class="metric">
                        <span class="metric-label">Top Flow</span>
                        <span class="metric-value">{top_baseline.get('top_flow', 'N/A')}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Top Strategy</span>
                        <span class="metric-value">{top_baseline.get('top_strategy', 'N/A')}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Top Algo</span>
                        <span class="metric-value">{top_baseline.get('top_algo', 'N/A')}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Top Sharpe</span>
                        <span class="metric-value">{float(top_baseline.get('top_test_sharpe', 0.0)):.4f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Optimization Gain</span>
                        <span class="metric-value">{optimization_label}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Optimization Status</span>
                        <span class="metric-value">{optimization_status}</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">
                        <span class="status-indicator active"></span>Proof Chain Live
                    </div>
                    <div class="metric">
                        <span class="metric-label">Chain Artifacts</span>
                        <span class="metric-value">{proof_chain_count}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Latest Proof Path</span>
                        <span class="metric-value">{proof_chain_latest_name}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Chain Status</span>
                        <span class="metric-value">{'LIVE' if proof_chain_count else 'MISSING'}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Rolling Live</span>
                        <span class="metric-value">{'YES' if rolling_live else 'NO'}</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">
                        <span class="status-indicator active"></span>Master Proof Board
                    </div>
                    <div class="metric">
                        <span class="metric-label">Live TXID Feed</span>
                        <span class="metric-value badge">{recent_txids[-1] if recent_txids else 'NONE'}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">TXIDs Tracked</span>
                        <span class="metric-value">{len(recent_txids)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Optimization Badge</span>
                        <span class="metric-value badge">{master_badge_state}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Live Proof Tempo</span>
                        <span class="metric-value">{rolling_points} points</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">TXID History</span>
                        <span class="metric-value">{', '.join(recent_txids[-3:]) if recent_txids else 'NONE'}</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">
                        <span class="status-indicator active"></span>Grant Readiness
                    </div>
                    <div class="metric">
                        <span class="metric-label">Alignments</span>
                        <span class="metric-value">{', '.join(alignments[:3]) or 'None'}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Proof Files</span>
                        <span class="metric-value">{proof_count}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Proposal Count</span>
                        <span class="metric-value">{len(grant_items)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Scan Coverage</span>
                        <span class="metric-value">{int(top_baseline.get('total_candidates', 0))}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Chain Files</span>
                        <span class="metric-value">{proof_chain_count}</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">
                        <span class="status-indicator active"></span>Trade Statistics
                    </div>
                    <div class="metric">
                        <span class="metric-label">Winning Trades</span>
                        <span class="metric-value">{winning_trades}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Losing Trades</span>
                        <span class="metric-value negative">{losing_trades}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Avg Win</span>
                        <span class="metric-value">${avg_win:.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Open Positions</span>
                        <span class="metric-value neutral">{open_positions}</span>
                    </div>
                </div>
            </div>
            
            <!-- Pyramid Milestones -->
            <div class="card">
                <div class="card-title">🎯 Capital Pyramid Progress (Luke Cadence)</div>
                <div class="pyramid">
                    <div class="pyramid-level {('active' if pyramid_level >= 1 else '')}">
                        <span>Level 1: $100</span>
                        <span>{'✅ ACTIVE' if pyramid_level >= 1 else '⏳ PENDING'}</span>
                    </div>
                    <div class="pyramid-level {('active' if pyramid_level >= 2 else '')}">
                        <span>Level 2: $100</span>
                        <span>{'✅ COMPLETE' if pyramid_level >= 2 else '⏳ PENDING'}</span>
                    </div>
                    <div class="pyramid-level {('active' if pyramid_level >= 3 else '')}">
                        <span>Level 3: $200 → 💸 WITHDRAW</span>
                        <span>{'✅ COMPLETE' if pyramid_level >= 3 else '⏳ PENDING'}</span>
                    </div>
                    <div class="pyramid-level {('active' if pyramid_level >= 4 else '')}">
                        <span>Level 4: $400</span>
                        <span>{'✅ COMPLETE' if pyramid_level >= 4 else '⏳ PENDING'}</span>
                    </div>
                    <div class="pyramid-level {('active' if pyramid_level >= 5 else '')}">
                        <span>Level 5: $800 → 💸 WITHDRAW</span>
                        <span>{'✅ COMPLETE' if pyramid_level >= 5 else '⏳ PENDING'}</span>
                    </div>
                </div>
            </div>
            
            <!-- Risk Status -->
            <div class="grid">
                <div class="card">
                    <div class="card-title">🛡️ Risk Management</div>
                    <div class="metric">
                        <span class="metric-label">Risk Level</span>
                        <span class="metric-value">{risk.get('risk_level', 'GREEN')}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Heat Score</span>
                        <span class="metric-value">{risk.get('heat_score', 0):.1f}/100</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Violations (24h)</span>
                        <span class="metric-value">{risk.get('recent_violations', 0)}</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">📊 Signal Gate Performance</div>
                    <div class="metric">
                        <span class="metric-label">Armed Rate</span>
                        <span class="metric-value">{signal_gate.get('armed_rate', 0):.1%}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Win Rate</span>
                        <span class="metric-value">{signal_gate.get('win_rate', 0):.1%}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">ML Model</span>
                        <span class="metric-value">{'TRAINED' if signal_gate.get('ml_model_trained') else 'TRAINING'}</span>
                    </div>
                </div>
            </div>
            
            <!-- Recent Trades -->
            <div class="card">
                <div class="card-title">📈 Recent Trade History</div>
                <table class="trades-table">
                    <thead>
                        <tr>
                            <th>TXID</th>
                            <th>Symbol</th>
                            <th>Direction</th>
                            <th>Entry Price</th>
                            <th>Qty</th>
                            <th>P&L</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    if trades:
        for trade in trades[-10:]:  # Show last 10 trades
            txid = trade.get('txid', 'N/A')[:16] + '...'
            symbol = trade.get('symbol', 'N/A')
            direction = trade.get('direction', 'N/A').upper()
            entry = trade.get('entry_price', 0)
            qty = trade.get('qty', 0)
            pnl = trade.get('pnl', 0)
            status = trade.get('status', 'UNKNOWN')
            pnl_color = 'negative' if pnl < 0 else ''
            
            html += f"""
                        <tr>
                            <td><span class="txid">{txid}</span></td>
                            <td>{symbol}</td>
                            <td>{direction}</td>
                            <td>${entry:.2f}</td>
                            <td>{qty:.6f}</td>
                            <td><span class="metric-value {pnl_color}">${pnl:.2f}</span></td>
                            <td>{status}</td>
                        </tr>
            """
    
    html += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <button class="refresh-btn" onclick="location.reload()">🔄</button>
        
        <div class="footer">
            <p>LUMENCORE INSTITUTIONAL HARMONIC TRADING SYSTEM | Powered by Monte Carlo Edge Detection</p>
            <p>Last Updated: <span id="footer-time"></span></p>
        </div>
        
        <script>
            // Update timestamp
            function updateTime() {
                const now = new Date().toLocaleString();
                document.getElementById('timestamp').innerText = now;
                document.getElementById('footer-time').innerText = now;
            }
            
            // Auto-refresh every 5 seconds
            setInterval(function() {
                location.reload();
            }, 5000);
            
            updateTime();
        </script>
    </body>
    </html>
    """
    
    return html

# Build and save dashboard
print("[BUILD] Generating institutional dashboard...")
dashboard_html = generate_dashboard_html()

dashboard_path = DASH / 'lumencore_dashboard.html'
with open(dashboard_path, 'w', encoding='utf-8') as f:
    f.write(dashboard_html)

print(f"✅ Dashboard created: {dashboard_path}")

# Open in browser
import webbrowser
webbrowser.open(f'file:///{dashboard_path}')

print("✅ Dashboard opened in browser")
print("🎯 Refreshes every 5 seconds | Click 🔄 to refresh manually")
