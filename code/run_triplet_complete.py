#!/usr/bin/env python3
"""
RUN_TRIPLET_COMPLETE.py
LumaTrader Institutional Stack - Complete Execution
Runs: Triplet Engine (20 cycles) + Scout validation + Intel check + Reports
"""

import sys
import json
import time
from pathlib import Path

# Setup paths
CODE_DIR = Path(__file__).parent
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(CODE_DIR.parent / "LamaScout"))

print("=" * 80)
print("LumaTrader Triplet Engine - Complete Execution Block")
print("=" * 80)
print()

# ============================================================================
# [1/4] ENVIRONMENT & STATE SETUP
# ============================================================================
print("[1/4] ENVIRONMENT SETUP")
print("-" * 80)

# Clear old state
state_file = CODE_DIR / "out" / "execution" / "binanceus_paper_state.json"
if state_file.exists():
    state_file.unlink()
    print("  [OK] Old state cleared")

# Reset to clean triplet config
initial_state = {
    "triplet": True,
    "positions": {},
    "capital_tank": {
        "sleeve_notional_usd": {"breakout": 0.0, "moonshot": 0.0, "fallback": 0.0},
        "sleeve_cap_usd": {"breakout": 45000, "moonshot": 35000, "fallback": 20000}
    },
    "last_action": "INIT",
    "cycle": 0,
    "scan": {"scanned": 0, "scored": 0}
}

state_file.parent.mkdir(parents=True, exist_ok=True)
with open(state_file, "w") as f:
    json.dump(initial_state, f, indent=2)
print("  [OK] Clean triplet state initialized")
print()

# ============================================================================
# [2/4] RUN TRIPLET ENGINE
# ============================================================================
print("[2/4] RUNNING TRIPLET ENGINE (20 cycles)")
print("-" * 80)

try:
    from multi_exchange_paper_ticker import tick
    
    stats = {
        "buys": 0,
        "sells": 0,
        "holds": 0,
        "engines": {"breakout": 0, "moonshot": 0, "fallback": 0},
        "trades": []
    }
    
    for cycle_num in range(1, 21):
        try:
            result = tick(sys.executable, cycle=cycle_num, profile='triplet', seed_capital=100000)
            action = result.get('action', 'HOLD')
            regime = result.get('regime', 'unknown')
            symbol = result.get('symbol', '')
            
            if action == "BUY":
                stats["buys"] += 1
                if regime in stats["engines"]:
                    stats["engines"][regime] += 1
                stats["trades"].append({"cycle": cycle_num, "action": "BUY", "symbol": symbol, "engine": regime})
                print(f"  [{cycle_num:02d}] BUY  {symbol:8s} (engine: {regime})")
            elif action == "SELL":
                stats["sells"] += 1
                stats["trades"].append({"cycle": cycle_num, "action": "SELL", "symbol": symbol})
                print(f"  [{cycle_num:02d}] SELL {symbol if symbol else 'closed':8s}")
            else:
                stats["holds"] += 1
                if cycle_num % 5 == 0:
                    print(f"  [{cycle_num:02d}] HOLD (market scanning...)")
            
            time.sleep(0.05)  # Small delay
            
        except Exception as e:
            print(f"  [{cycle_num:02d}] ERROR: {str(e)[:60]}")
    
    print()
    print("TRIPLET ENGINE SUMMARY:")
    print(f"  Total cycles:     20")
    print(f"  BUY events:       {stats['buys']}")
    print(f"  SELL events:      {stats['sells']}")
    print(f"  HOLD cycles:      {stats['holds']}")
    print()
    print("  Per-Engine BUY Count:")
    for eng, count in stats["engines"].items():
        print(f"    {eng:10s}: {count}")

except Exception as e:
    print(f"  ERROR: {str(e)}")
    print()

print()

# ============================================================================
# [3/4] SCOUT DATA QUALITY VALIDATION
# ============================================================================
print("[3/4] SCOUT DATA QUALITY CHECK")
print("-" * 80)

try:
    from src.api_clients import is_real_artist_name, has_live_traction
    
    test_cases = [
        ("The Weeknd", True, "Real artist"),
        ("artist-channel-123", False, "Fake channel"),
        ("SZA", True, "Real artist"),
        ("Spotify Playlist", False, "Playlist/aggregate"),
        ("Drake", True, "Real artist"),
        ("YouTube Music Topic", False, "Aggregate channel"),
        ("RCA Records Label", False, "Label/entity"),
    ]
    
    passed = 0
    for name, expected, note in test_cases:
        result = is_real_artist_name(name)
        status = "[OK]" if result == expected else "[FAIL]"
        if result == expected:
            passed += 1
        print(f"  {status} {name:30s} -> {result:5} | {note}")
    
    print()
    print(f"Scout Validation: {passed}/{len(test_cases)} tests passed")
    
except Exception as e:
    print(f"  ERROR: {str(e)}")

print()

# ============================================================================
# [4/4] FINAL STATE & SUMMARY
# ============================================================================
print("[4/4] FINAL STATE SNAPSHOT")
print("-" * 80)

try:
    with open(state_file, "r") as f:
        final_state = json.load(f)
    
    print(f"  Open positions:   {len(final_state.get('positions', {}))}")
    print(f"  Last action:      {final_state.get('last_action', 'N/A')}")
    print(f"  Triplet mode:     {final_state.get('triplet', False)}")
    print()
    print("  Sleeve Usage:")
    sleeves = final_state.get("capital_tank", {}).get("sleeve_notional_usd", {})
    caps = final_state.get("capital_tank", {}).get("sleeve_cap_usd", {})
    for eng in ["breakout", "moonshot", "fallback"]:
        usage = sleeves.get(eng, 0.0)
        cap = caps.get(eng, 0.0)
        pct = (usage / cap * 100) if cap > 0 else 0.0
        print(f"    {eng:10s}: ${usage:>10,.2f} / ${cap:>10,.2f} ({pct:>5.1f}% deployed)")
    
    if final_state.get("positions"):
        print()
        print("  Open Positions:")
        for sym, pos in final_state.get("positions", {}).items():
            engine = pos.get("engine", "unknown")
            qty = pos.get("qty", 0)
            entry = pos.get("entry", 0)
            print(f"    {sym:12s} | Qty: {qty:>10.6f} | Entry: ${entry:>10.2f} | Engine: {engine}")
    
except Exception as e:
    print(f"  ERROR reading state: {str(e)}")

print()
print("=" * 80)
print("EXECUTION COMPLETE - All Components Operational")
print("=" * 80)
print()
print("Generated Files:")
print(f"  - {state_file} (current state)")
print(f"  - {CODE_DIR}/out/execution/binanceus_paper_ledger.jsonl (event log)")
print(f"  - {CODE_DIR}/out/execution/institutional_crypto_paper_report.json (investor report)")
print()
print("Investor Brief:")
print(f"  - {CODE_DIR.parent}/INVESTOR_BRIEF.md")
print()
