#!/usr/bin/env python3
"""
Fix execution_orchestrator.py: replace messy lines 1-245 with clean init block.
Run from repo root: python fix_init.py
"""
from pathlib import Path

SRC = Path("code/execution/execution_orchestrator.py")

with open(SRC, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

CLEAN_HEADER = """\
# =============================================================================
# LumaTrader™ — LumenCore Universal Execution Orchestrator
# Production-grade multi-exchange trading engine with harmonic intelligence
# =============================================================================

import sys
import os
import time
import json
import subprocess
import hashlib
import hmac
import base64
import urllib.parse
import signal
import threading
import uuid
import re
import traceback
import inspect
import glob
import logging
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests

# Ensure local code paths are on sys.path before local imports
sys.path.insert(0, r'C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code')
sys.path.insert(0, r'C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code\\execution')

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from signal_gate import EvolutionarySignalGate, GateInput
import signal_gate
from portfolio_brain import PortfolioBrain, Position
from liquidity_guard import LiquidityGuard, LiquiditySnapshot
from risk_kernel import RiskKernel, RiskState
from rl_policy import RLPolicy
from sector_rotation import SectorRotation

try:
    from execution.harmonic_signal_connector import HarmonicSignalConnector
    from execution.live_runtime_guard import LiveRuntimeGuard
    from execution.audit_chain import AuditChain
except Exception:
    from harmonic_signal_connector import HarmonicSignalConnector
    from live_runtime_guard import LiveRuntimeGuard
    from audit_chain import AuditChain

try:
    from arch.univariate import arch_model
    ARCH_AVAILABLE = True
except Exception:
    arch_model = None
    ARCH_AVAILABLE = False

RiverMean = None
RiverVar = None
RIVER_AVAILABLE = False

# === Configuration paths ===
ROOT = Path(r'C:\\LumaTrader\\INSTITUTIONAL_STACK_V2')
OUT = ROOT / 'out' / 'execution'
CONFIG = ROOT / 'config'
ENV_FILE = CONFIG / 'luma_live_keys.env'
RUNTIME_FILE = CONFIG / 'runtime_control.json'
RUNTIME_PROFILE_LOCK_FILE = CONFIG / 'runtime_profile_lock.json'
AUDIT_CHAIN_FILE = OUT / 'execution_audit_chain.jsonl'
ADAPTIVE_PROFILE_FILE = OUT / 'adaptive_profile_state.json'
PAYOUT_INTENTS_FILE = OUT / 'payout_intents.json'
WALLET_TRANSFER_REQUESTS_FILE = OUT / 'wallet_transfer_requests.json'
LIVE_BALANCE_SNAPSHOT_FILE = OUT / 'live_balance_snapshot.json'
X1000_CONTROL_PLANE_FILE = ROOT / 'code' / 'x1000_control_plane.py'
LIVE_MARKET_STREAM_STATUS_FILE = OUT / 'live_market_stream_status.json'
LIVE_RESELECTION_STATUS_FILE = OUT / 'live_reselection_status.json'
LIVE_ENGINE_HEARTBEAT_FILE = OUT / 'live_engine_heartbeat.json'
EXECUTION_LOCK_FILE = OUT / '.execution_lock'

# Rolling capital paths
ROLLING_CAPITAL_BEST_MULTI_PATH = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_best_multi.json")
ROLLING_CAPITAL_HEATMAP_PATH = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_heatmap.json")
ROLLING_CAPITAL_BEST_PATH = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_best.json")

OUT.mkdir(parents=True, exist_ok=True)

# === Control flow variables (initialized once at module load) ===
auto_stop_triggered = False
auto_boost_active = False
auto_stop_reason = None
auto_boost_reason = None
current_drawdown = None
risk_reasons = []
win_streak = None

print("\\u001b[36m\\u2728 LUMENCORE UNIVERSAL EXECUTION ORCHESTRATOR\\u001b[0m")
print("=" * 70)
print("Signal Engine \\u2192 Full Symbol Range \\u2192 Multi-Exchange Routing")
print("=" * 70)

"""

# Replace lines 0:245 (messy init) with clean header
# Lines 245+ (0-indexed) start with load_api_keys() at line 246 (1-indexed)
new_content = CLEAN_HEADER + "".join(lines[245:])

# Also remove any remaining "# === ENSURE CONTROL VARIABLES" duplicate block near line 3450
# that re-initializes auto_stop_triggered etc. before the while loop
# (these are now initialized once at module level above)
# Find and remove the duplicate init block before the while loop
dupe_marker = "# === ENSURE CONTROL VARIABLES ARE ALWAYS IN SCOPE FOR MAIN LOOP ==="
if dupe_marker in new_content:
    # Find the block and remove just the variable declarations (not the while True)
    idx = new_content.find(dupe_marker)
    end_idx = new_content.find("loop_count = 0", idx)
    if end_idx > idx:
        new_content = new_content[:idx] + new_content[end_idx:]
        print(f"Removed duplicate control variable block at position {idx}")

with open(SRC, "w", encoding="utf-8") as f:
    f.write(new_content)

new_lines = new_content.count("\n")
print(f"Original: {len(lines)} lines")
print(f"New: ~{new_lines} lines")
print("Init section cleaned: duplicates removed, time.sleep(2) removed, debug prints removed")
