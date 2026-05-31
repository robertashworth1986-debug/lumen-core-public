import json, os, glob, time
from datetime import datetime, timezone

print('=' * 64)
print('  MOONSHOT SCANNER — ' + datetime.now().strftime('%H:%M:%S'))
print('=' * 64)

# 1. Symbol flip intel
intel_path = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\symbol_flip_intel_top5.json'
if os.path.exists(intel_path):
    d = json.load(open(intel_path, encoding='utf-8'))
    age_s = d.get('age_sec', '?')
    print(f'\n[SYMBOL FLIP INTEL]  age={age_s}s')
    syms = d.get('symbols', d.get('top_symbols', d.get('candidates', [])))
    for s in syms[:15]:
        if isinstance(s, dict):
            sym    = str(s.get('symbol', s.get('pair', '?'))).replace('/USD','').replace('USD','')
            score  = s.get('score', s.get('hybrid_score', s.get('composite_score', '?')))
            mom    = s.get('momentum_pct', s.get('momentum', '?'))
            regime = s.get('regime', s.get('regime_label', ''))
            trend  = s.get('trend_label', s.get('trend', ''))
            vol    = s.get('volume_usd_24h', s.get('turnover_usd', ''))
            print(f'  {sym:<10} score={score!s:<8} mom={mom!s:<8} regime={regime!s:<12} trend={trend!s:<8} vol={vol!s}')
        else:
            print(' ', s)

# 2. Latest alpha map
alpha_files = sorted(
    glob.glob(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\ops\kraken_alpha_map*.json')
    + glob.glob(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\ops\alpha_map*.json')
    + glob.glob(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\kraken_alpha*.json'),
    key=os.path.getmtime
)
if alpha_files:
    af = alpha_files[-1]
    mtime = datetime.fromtimestamp(os.path.getmtime(af)).strftime('%Y-%m-%d %H:%M')
    print(f'\n[ALPHA MAP: {os.path.basename(af)}  written={mtime}]')
    d = json.load(open(af, encoding='utf-8'))
    rows = d.get('ranked', d.get('symbols', d.get('results', d.get('top', []))))
    for r in rows[:20]:
        if isinstance(r, dict):
            sym   = str(r.get('symbol', r.get('pair', '?'))).replace('/USD','').replace('USD','')
            score = r.get('composite_score', r.get('score', r.get('alpha_score', r.get('hybrid_score', '?'))))
            mom   = r.get('momentum_pct', r.get('momentum', '?'))
            sprd  = r.get('spread_bps', '?')
            vol   = r.get('volume_usd_24h', r.get('turnover_usd', '?'))
            print(f'  {sym:<10} score={score!s:<8} mom={mom!s:<8} spread={sprd!s:<6} vol24h={vol!s}')
else:
    print('\n[ALPHA MAP: no files found]')

# 3. Approval queue — what the executor thinks right now
q_path = r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\live_operator_approval_queue.json'
if os.path.exists(q_path):
    d = json.load(open(q_path, encoding='utf-8'))
    print(f'\n[LIVE QUEUE: {d.get("selected_symbol","?")} ranked {d.get("queue_count","?")} candidates]')
    for t in d.get('tickets', [])[:8]:
        m = t.get('scanner_meta', {})
        sym     = t.get('symbol', '?')
        rank    = t.get('rank', '?')
        hs      = m.get('hybrid_score', '?')
        mom     = m.get('momentum_pct', '?')
        sprd    = m.get('spread_bps', '?')
        eligible = 'HYBRID-ELIGIBLE' if m.get('hybrid_eligible') else ''
        print(f'  #{rank} {sym:<10} hybrid={hs!s:<8} mom={mom!s:<8} spread={sprd!s:<6} {eligible}')

# 4. Summary — top moonshot picks
print('\n' + '=' * 64)
print('  MOONSHOT VERDICT')
print('=' * 64)
