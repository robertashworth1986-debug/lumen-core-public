#!/usr/bin/env python3
"""
Unified Trading System Launcher
================================
Legacy simulation launcher. It does not provide a production live path:
  1. unified_alpha_engine.py — finds alpha signals (arbitrage, momentum, value)
  2. unified_trade_executor.py — executes trades on those signals (paper or live)
  3. Wires both into luma_experience_gateway for real-time dashboard visibility

Usage:
  # Paper trading (simulated, safe)
  python launch_unified_trading.py --mode paper --daemon
  
  # Live mode is rejected. Use execution/live_executor.py after readiness gates.
  
  # Single cycle test
  python launch_unified_trading.py --mode paper

Features:
  - Alpha discovery: 45-second scan for signals across thousands of symbols
  - Trade execution: 30-second cycle executes and prices positions
  - Real-time metrics: All stats published to gateway APIs
  - Paper mode: Safe validation before going live
  - Live mode: Real money with same logic, approval gated
  - 5-day lookback: Validates signal quality and Closing Line Value (CLV)
  - Moonshot detection: Scores extreme payoff opportunities (10→1000)

Integration:
  - Gateway APIs: /api/trading/* endpoints pull live metrics
  - Dashboard: Unified Trading card shows real P&L + alpha signals
  - Approval: Approval queue gates live orders until user approves
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
ALPHA_ENGINE = CODE / "unified_alpha_engine.py"
TRADE_EXECUTOR = CODE / "unified_trade_executor.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LAUNCHER] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Process Management
# ─────────────────────────────────────────────────────────────────────────────

class ProcessManager:
    """Manages both engine processes with auto-restart on failure."""
    
    def __init__(self, mode: str = "paper"):
        self.mode = mode
        self.alpha_process = None
        self.executor_process = None
        self.running = True
    
    def start_alpha_engine(self):
        """Start alpha discovery engine."""
        logger.info("Starting unified alpha engine...")
        env = os.environ.copy()
        env["UNIFIED_ALPHA_SCAN_SEC"] = "45"
        
        self.alpha_process = subprocess.Popen(
            [sys.executable, str(ALPHA_ENGINE), "--daemon"],
            env=env,
            cwd=str(CODE),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(f"Alpha engine started (PID {self.alpha_process.pid})")
    
    def start_trade_executor(self):
        """Start trade execution engine."""
        logger.info(f"Starting trade executor in {self.mode.upper()} mode...")
        env = os.environ.copy()
        env["UNIFIED_EXECUTOR_SCAN_SEC"] = "30"
        env["UNIFIED_EXECUTOR_MODE"] = self.mode
        env["UNIFIED_EXECUTOR_BANKROLL"] = "100000.0"
        
        self.executor_process = subprocess.Popen(
            [sys.executable, str(TRADE_EXECUTOR), "--daemon", "--mode", self.mode],
            env=env,
            cwd=str(CODE),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(f"Trade executor started (PID {self.executor_process.pid})")
    
    def start_all(self):
        """Start both engines."""
        self.start_alpha_engine()
        time.sleep(2)  # Stagger startup
        self.start_trade_executor()
    
    def stop_all(self):
        """Stop both engines gracefully."""
        logger.info("Stopping all engines...")
        
        if self.executor_process and self.executor_process.poll() is None:
            self.executor_process.terminate()
            try:
                self.executor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.executor_process.kill()
            logger.info("Trade executor stopped")
        
        if self.alpha_process and self.alpha_process.poll() is None:
            self.alpha_process.terminate()
            try:
                self.alpha_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.alpha_process.kill()
            logger.info("Alpha engine stopped")
        
        self.running = False
    
    def check_health(self):
        """Check if engines are still running, restart if needed."""
        alpha_ok = self.alpha_process and self.alpha_process.poll() is None
        executor_ok = self.executor_process and self.executor_process.poll() is None
        
        if not alpha_ok:
            logger.warning("Alpha engine died, restarting...")
            self.start_alpha_engine()
        
        if not executor_ok:
            logger.warning("Trade executor died, restarting...")
            self.start_trade_executor()
        
        return alpha_ok and executor_ok
    
    async def monitor_loop(self, interval: float = 10.0):
        """Monitor engines and restart if needed."""
        logger.info(f"Starting monitor loop (check every {interval}s)...")
        while self.running:
            try:
                self.check_health()
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                self.stop_all()
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(interval)


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified Trading System Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_unified_trading.py --mode paper --daemon
    → Start paper trading with live updates
  
  python launch_unified_trading.py --mode live --daemon
    → Start live trading (requires approval for orders)
  
  python launch_unified_trading.py --mode paper
    → Run single cycle for testing
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default="paper",
        help="Trading mode (default: paper)"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously with auto-restart on failure"
    )
    
    args = parser.parse_args()

    if args.mode == "live":
        parser.error(
            "live mode is disabled: unified_alpha_engine uses stub market data "
            "and unified_trade_executor simulates fills."
        )
    if os.environ.get("LUMA_ENABLE_LEGACY_SIMULATION") != "1":
        parser.error(
            "legacy unified simulation is retired from production. Set "
            "LUMA_ENABLE_LEGACY_SIMULATION=1 only for isolated development."
        )
    
    logger.info(f"Unified Trading System Launcher v1.0")
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info(f"Daemon: {args.daemon}")
    
    manager = ProcessManager(mode=args.mode)
    
    try:
        if args.daemon:
            manager.start_all()
            asyncio.run(manager.monitor_loop())
        else:
            # Single cycle mode
            logger.info("Running single cycle...")
            
            # Run alpha engine once
            subprocess.run(
                [sys.executable, str(ALPHA_ENGINE)],
                cwd=str(CODE),
                check=False
            )
            
            # Run executor once
            env = os.environ.copy()
            env["UNIFIED_EXECUTOR_MODE"] = args.mode
            subprocess.run(
                [sys.executable, str(TRADE_EXECUTOR)],
                env=env,
                cwd=str(CODE),
                check=False
            )
            
            logger.info("Single cycle complete")
    
    except KeyboardInterrupt:
        logger.info("Interrupted")
        manager.stop_all()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        manager.stop_all()
        sys.exit(1)


if __name__ == "__main__":
    main()
