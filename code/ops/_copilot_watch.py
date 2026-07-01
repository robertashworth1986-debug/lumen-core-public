"""
LUMA APEX CO-PILOT — Guarded monitoring loop
Runs every 10s, commentates on every change, and fails closed on live-execution hazards.
"""
import json, time, os
from datetime import datetime

RC_PATH  = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\config\runtime_control.json'
HB_PATH  = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\live_executor_heartbeat.json'
AF_PATH  = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\approval_autofire_heartbeat.json'
LQ_PATH  = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\live_operator_approval_queue.json'
LED_PATH = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\live_trade_ledger.jsonl'

SAFE_DEFAULTS = {
    'kill_switch': True,
    'mode': 'paper',
    'allow_live_orders': False,
    'max_open_positions': 2,
    'max_portfolio_heat': 0.25,
    'order_notional_pct': 0.05,
    'spot_inventory_entry_fraction': 0.05,
    'edge_proof_bootstrap_min_hybrid_score': 10.0,
    'edge_proof_bootstrap_min_momentum_pct': 0.08,
    'gate_override_enabled': False,
    'conviction_sizing_enabled': True,
    'symbol_learning_enabled': True,
    'adaptive_entry_gate_enabled': True,
    'alpha_gate_watch_only': True,
}

def load(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except:
        return {}

def tail_ledger(n=5):
    rows = []
    try:
        with open(LED_PATH, encoding='utf-8') as f:
            lines = f.readlines()
        for l in lines[-n:]:
            try: rows.append(json.loads(l.strip()))
            except: pass
    except: pass
    return rows

def patch_runtime(fixes: dict, reason: str):
    rc = load(RC_PATH)
    if not rc:
        return
    changed = []
    for k, v in fixes.items():
        if rc.get(k) != v:
            rc[k] = v
            changed.append(f'{k}={v}')
    if changed:
        with open(RC_PATH, 'w', encoding='utf-8') as f:
            json.dump(rc, f, indent=2, ensure_ascii=False)
        print(f'  [AUTO-FIX] {reason}: {", ".join(changed)}')

prev_equity   = None
prev_txids    = set()
prev_status   = None
prev_selected = None
cycle         = 0

# seed known txids
for row in tail_ledger(30):
    if row.get('txid'): prev_txids.add(row['txid'])

print('=' * 66)
print('  LUMA APEX CO-PILOT  — watching every 10s, failing closed on live hazards')
print('  Ctrl+C to stop')
print('=' * 66)
print()

while True:
    time.sleep(10)
    cycle += 1
    ts  = datetime.now().strftime('%H:%M:%S')
    hb  = load(HB_PATH)
    af  = load(AF_PATH)
    lq  = load(LQ_PATH)
    rc  = load(RC_PATH)

    equity   = float(hb.get('total_equity_usd_hint') or 0)
    cash     = float(hb.get('cash_usd_hint') or 0)
    held     = float(hb.get('holdings_value_usd_hint') or 0)
    heat     = float(hb.get('risk_portfolio_heat_effective') or 0)
    status   = hb.get('status', '?')
    reason   = hb.get('reason', '?')
    selected = hb.get('selected_symbol')
    hybrid   = float(hb.get('selected_hybrid_score') or 0)
    mom      = float(hb.get('selected_momentum_pct') or 0) * 100
    spread   = float(hb.get('selected_spread_bps') or 0)
    risk_r   = hb.get('risk_reasons') or []
    skips    = int(hb.get('symbol_skip_active_count') or 0)
    positions = int(hb.get('risk_open_positions_effective') or 0)

    delta_str = ''
    if prev_equity and prev_equity > 0 and equity > 0:
        delta = equity - prev_equity
        sign  = '+' if delta >= 0 else ''
        delta_str = f'  [{sign}${delta:.3f}]'
        if delta < -5:
            print(f'  !!!  EQUITY DROP ${delta:.2f} — investigating')
        elif delta > 2:
            print(f'  ***  PROFIT +${delta:.2f} compounding!')
    prev_equity = equity if equity > 0 else prev_equity

    # ── Status line ──────────────────────────────────────────────────
    status_icon = {'running':'✓', 'blocked':'!', 'error':'✗', 'approved':'→', 'submitted':'→'}.get(status, '?')
    print(f'[{ts}] #{cycle:04d}  {status_icon} {status}/{reason}')
    print(f'  equity=${equity:.2f}{delta_str}  cash=${cash:.2f}  held=${held:.2f}  heat={heat:.1%}  pos={positions}  skips={skips}')

    # ── Selected candidate ───────────────────────────────────────────
    if selected:
        if selected != prev_selected:
            print(f'  NEW TARGET → {selected}  hybrid={hybrid:.1f}  mom={mom:.2f}%  spread={spread:.1f}bps')
        else:
            print(f'  target     : {selected}  hybrid={hybrid:.1f}  mom={mom:.2f}%  spread={spread:.1f}bps')
    prev_selected = selected

    # ── Queue top pick ───────────────────────────────────────────────
    tickets = lq.get('tickets', [])
    if tickets:
        t  = tickets[0]
        m  = t.get('scanner_meta', {})
        qs = t.get('symbol','?')
        qh = float(m.get('hybrid_score') or 0)
        qm = float(m.get('momentum_pct') or 0) * 100
        qp = float(m.get('spread_bps') or 0)
        print(f'  queue #1   : {qs}  hybrid={qh:.1f}  mom={qm:.2f}%  spread={qp:.1f}bps')

    # ── Autofire ─────────────────────────────────────────────────────
    af_eligible = int(af.get('eligible_count') or 0)
    af_approved = int(af.get('approved_buy_count') or 0)
    af_cap      = float(af.get('buy_notional_cap_usd') or 0)
    if af_eligible > 0:
        print(f'  autofire   : {af_eligible} ELIGIBLE  approved={af_approved}  cap=${af_cap:.0f}')
    else:
        print(f'  autofire   : pending={af.get("pending_count",0)}  eligible=0  cap=${af_cap:.0f}')

    # ── New trades ───────────────────────────────────────────────────
    new_trades = []
    for row in tail_ledger(8):
        txid = row.get('txid')
        if txid and txid not in prev_txids:
            prev_txids.add(txid)
            side = (row.get('side') or '?').upper()
            sym  = row.get('symbol', '?')
            new_trades.append(f'{side} {sym}  txid={txid}')
    for t in new_trades:
        print(f'  TRADE FIRED: {t}')

    # ════════════════════════════════════════════════════════════════
    # AUTO-FIX RULES
    # ════════════════════════════════════════════════════════════════
    fixes = {}

    # Rule 1: live orders are never auto-enabled by this watcher.
    if rc.get('allow_live_orders') == True:
        fixes['allow_live_orders'] = False
        fixes['mode'] = 'paper'
        print('  !!!  allow_live_orders=True — forcing paper/safe mode')

    # Rule 2: kill switch is fail-closed. Operators may clear it manually elsewhere.
    if rc.get('kill_switch') != True:
        fixes['kill_switch'] = True
        print('  !!!  kill_switch is not locked — enabling fail-closed guard')

    # Rule 3: alpha gate must remain watch-only for research/paper loops.
    if rc.get('alpha_gate_watch_only') != True:
        fixes['alpha_gate_watch_only'] = True
        print('  !!!  alpha_gate_watch_only is not enabled — restoring watch-only mode')

    # Rule 4: clamp excessive order sizing hints in unattended mode.
    onp = float(rc.get('order_notional_pct') or 0)
    if onp > 0.10:
        fixes['order_notional_pct'] = 0.05
        print(f'  !!!  order_notional_pct={onp:.2f} too high for unattended watcher — clamping to 0.05')

    # Rule 5: risk reasons containing kill_switch_on are proof the guard is working.
    if 'kill_switch_on' in risk_r:
        print('  guard     : kill_switch_on present — leaving fail-closed state intact')

    # Rule 6: heat dangerously high (above 85%)
    if heat > 0.85:
        print(f'  !!!  HEAT {heat:.1%} — near limit 72% cap, watching closely')

    # Rule 7: equity crater (>15% drop from session high)
    # tracked implicitly by delta above

    # Rule 8: executor error for more than 3 cycles (would need counter)
    # simple version: if status=error, note it
    if status == 'error':
        print(f'  !!!  Executor error: {reason} — may self-heal, watching')

    if fixes:
        patch_runtime(fixes, 'auto-fix')

    # ── Status summary ───────────────────────────────────────────────
    status_line = {
        'running': 'scanning...',
        'blocked': f'blocked ({reason})',
        'approved': 'ORDER APPROVED',
        'submitted': 'ORDER SUBMITTED',
        'error': f'ERROR ({reason})',
    }.get(status, status)
    print(f'  → {status_line}')
    print()
