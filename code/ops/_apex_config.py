import json
path = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\config\runtime_control.json'
with open(path, encoding='utf-8') as f:
    rc = json.load(f)

apex = {
    # Gate aggression
    'gate_override_enabled': True,
    'gate_override_min_confidence': 0.52,
    'gate_override_min_edge_bps': 6.0,
    'hard_safety_only_mode': True,
    'alpha_gate_watch_only': False,
    # Position sizing
    'spot_inventory_entry_fraction': 0.55,
    'max_symbol_allocation_pct': 0.62,
    # Pounce / urgency
    'pounce_edge_bps_bonus': 25.0,
    # Conviction sizing
    'conviction_sizing_enabled': True,
    'conviction_sizing_scale': 2.0,
    # Swing / momentum
    'hybrid_swing_enabled': True,
    'hybrid_long_bias_enabled': True,
    'hybrid_long_bias_min_momentum_pct': 0.02,
    # Symbol learning
    'symbol_learning_enabled': True,
    'symbol_learning_stale_hours': 48,
    # Universe scan
    'universe_scan_cap': 2000,
    'max_spread_bps': 35.0,
    # Adaptive gate
    'adaptive_entry_gate_enabled': True,
    'adaptive_entry_gate_starvation_sec': 35.0,
    'adaptive_entry_gate_tighten_step_bps': 1.5,
    'adaptive_entry_gate_recent_trades': 3,
    # Safety floors
    'kill_switch': False,
    'max_open_positions': 10,
    'max_portfolio_heat': 0.72,
    'loop_seconds': 5,
}

rc.update(apex)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(rc, f, indent=2, ensure_ascii=False)

print('APEX PREDATOR CONFIG LIVE')
for k, v in apex.items():
    print('  ' + k + ': ' + str(v))
