import json, time
from datetime import datetime

hb_path   = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\live_executor_heartbeat.json'
af_path   = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\approval_autofire_heartbeat.json'
ledger_path = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\live_trade_ledger.jsonl'

def tail_ledger(n=20):
    with open(ledger_path, encoding='utf-8') as f:
        lines = f.readlines()
    out = []
    for l in lines[-n:]:
        try: out.append(json.loads(l.strip()))
        except: pass
    return out

# seed known TXIDs
prev_txids = set()
try:
    for row in tail_ledger(30):
        if row.get('txid'): prev_txids.add(row['txid'])
except: pass

prev_equity = None
print('Monitoring 8 cycles (every 15s) ...')
print('-' * 64)

for cycle in range(1, 9):
    time.sleep(15)
    ts = datetime.now().strftime('%H:%M:%S')

    hb = json.load(open(hb_path, encoding='utf-8'))
    af = json.load(open(af_path, encoding='utf-8'))

    equity      = hb.get('total_equity_usd_hint', 0)
    cash        = hb.get('cash_usd_hint', 0)
    held        = hb.get('holdings_value_usd_hint', 0)
    status      = hb.get('status','?') + ' / ' + hb.get('reason','?')
    largest_sym = hb.get('largest_holding_symbol','—')
    largest_pct = hb.get('largest_holding_weight_pct', 0)
    skip_count  = hb.get('symbol_skip_active_count', 0)
    selected    = hb.get('selected_symbol', '—')
    h_score     = hb.get('selected_hybrid_score', '—')

    delta = ''
    if prev_equity is not None:
        d = equity - prev_equity
        delta = f'  ({"+" if d >= 0 else ""}{d:.3f})'
    prev_equity = equity

    # detect new trades
    new_trades = []
    try:
        for row in tail_ledger(10):
            txid = row.get('txid')
            if txid and txid not in prev_txids:
                prev_txids.add(txid)
                new_trades.append(
                    f"{row.get('side','?').upper():4s}  {row.get('symbol','?'):8s}  txid={txid}"
                )
    except: pass

    print(f'[{ts}]  Cycle {cycle}/8')
    print(f'  equity   : ${equity:.3f}{delta}')
    print(f'  cash     : ${cash:.3f}   held: ${held:.3f}')
    print(f'  largest  : {largest_sym} ({largest_pct:.1f}%)   skips: {skip_count}')
    print(f'  selected : {selected}  score={h_score}')
    print(f'  status   : {status}')
    print(f'  autofire : pending={af.get("pending_count",0)}  eligible={af.get("eligible_count",0)}  '
          f'approved_buy={af.get("approved_buy_count",0)}  cap=${af.get("buy_notional_cap_usd",0)}')
    if new_trades:
        for t in new_trades:
            print(f'  *** TRADE FIRED: {t}')
    else:
        print(f'  (no new trades this cycle)')
    print()
