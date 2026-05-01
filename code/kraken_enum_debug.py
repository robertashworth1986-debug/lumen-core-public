import json
try:
    from BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS import build_from_kraken, merged_env
    out = {}
    pairs = build_from_kraken(merged_env())
    out['kraken_pair_count'] = len(pairs)
    out['kraken_sample'] = pairs[:10]
    out['success'] = True
except Exception as e:
    out = {'error': str(e), 'success': False}
with open('kraken_enum_debug_out.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)