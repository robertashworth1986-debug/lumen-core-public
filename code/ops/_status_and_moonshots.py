import json, time

time.sleep(20)

hb  = json.load(open(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\live_executor_heartbeat.json', encoding='utf-8'))
lq  = json.load(open(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\live_operator_approval_queue.json', encoding='utf-8'))
af  = json.load(open(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\approval_autofire_heartbeat.json', encoding='utf-8'))
intel = json.load(open(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\symbol_flip_intel_top5.json', encoding='utf-8'))

print('=== LIVE STATUS ===')
print('status   :', hb.get('status'), '/', hb.get('reason'))
print('selected :', hb.get('selected_symbol'), '| hybrid:', round(float(hb.get('selected_hybrid_score') or 0), 2), '| mom:', round(float(hb.get('selected_momentum_pct') or 0)*100, 3), '%')
print('equity   : $' + str(round(float(hb.get('total_equity_usd_hint') or 0), 2)))
print('cash     : $' + str(round(float(hb.get('cash_usd_hint') or 0), 2)))
print('holdings : $' + str(round(float(hb.get('holdings_value_usd_hint') or 0), 2)))
print('positions:', hb.get('risk_open_positions_effective'), '/', hb.get('risk_max_open_positions'))
print('heat     :', round(float(hb.get('risk_portfolio_heat_effective') or 0), 3))
print('risk     :', hb.get('risk_reasons'))
print()

print('=== QUEUE TOP 5 (executor pick) ===')
for t in lq.get('tickets', [])[:5]:
    m = t.get('scanner_meta', {})
    rank  = t.get('rank', '?')
    sym   = t.get('symbol', '?')
    hs    = round(float(m.get('hybrid_score') or 0), 2)
    mom   = round(float(m.get('momentum_pct') or 0) * 100, 3)
    sprd  = round(float(m.get('spread_bps') or 0), 1)
    eli   = 'HYBRID-READY' if m.get('hybrid_eligible') else ''
    print(f'  #{rank} {sym:<10} hybrid={hs:<7} mom={mom}%  spread={sprd}bps  {eli}')

print()
print('=== ALPHA INTEL TOP 5 (multi-TF) ===')
for c in intel.get('long_candidates', [])[:5]:
    sym   = c.get('symbol', '?')
    score = round(float(c.get('alpha_long_score') or 0), 2)
    mode  = c.get('strategy_mode', '?')
    print(f'  {sym:<10} alpha={score:<7} mode={mode}')

print()
print('autofire: eligible=', af.get('eligible_count'), ' approved_buy=', af.get('approved_buy_count'), ' cap=$' + str(af.get('buy_notional_cap_usd')))

print()
print('=== MOONSHOT VERDICT ===')
# Cross-reference queue + intel
queue_top = {t['symbol']: t.get('scanner_meta',{}) for t in lq.get('tickets',[])}
intel_top  = {c['symbol']: c for c in intel.get('long_candidates',[])}
skips = set(hb.get('symbol_skip_list', []))
print('Top picks right now (cross-referenced):')
candidates = []
for sym, m in queue_top.items():
    hs   = float(m.get('hybrid_score') or 0)
    mom  = float(m.get('momentum_pct') or 0)
    sprd = float(m.get('spread_bps') or 0)
    alpha = float(intel_top.get(sym, {}).get('alpha_long_score') or 0)
    combined = hs + alpha * 0.5
    candidates.append((combined, sym, hs, mom * 100, sprd, alpha))
candidates.sort(reverse=True)
for combined, sym, hs, mom, sprd, alpha in candidates:
    tag = '[IN INTEL]' if alpha > 0 else ''
    print(f'  {sym:<10} combined={combined:.1f}  hybrid={hs:.1f}  mom={mom:.3f}%  spread={sprd:.1f}bps  alpha={alpha:.1f}  {tag}')
