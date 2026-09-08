"""Bounded, read-only discovery. Reports are leads, never measured savings.

No posting, private-message access, account changes, recurring jobs or production
writes. Reddit reads use the existing documented environment variable names.
Missing credentials or rejected access are recorded as HOLD, never bypassed.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, math, os, re, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

CF = 'https://www.cloudflarestatus.com/api/v2/incidents/unresolved.json'
SUBS = ('sysadmin', 'devops', 'datacenter')
MAX_BYTES = 2_000_000
KEYS = ('REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_REFRESH_TOKEN')
UA = 'LumenCoreConstraintDiscovery/0.1 (read-only; bounded research)'

def now() -> datetime:
    return datetime.now(timezone.utc)

def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat()

def canonical(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def request(url: str, headers: dict | None = None, data: bytes | None = None) -> tuple[dict, bytes]:
    allowed = {'www.cloudflarestatus.com', 'www.reddit.com', 'oauth.reddit.com'}
    p = urllib.parse.urlparse(url)
    if p.scheme != 'https' or p.hostname not in allowed or p.username or p.password:
        raise ValueError('Unapproved source host')
    h = {'User-Agent': UA, **(headers or {})}
    with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, data=data, headers=h), timeout=20) as r:
        if r.status != 200: raise ValueError('Non-success response')
        blob = r.read(MAX_BYTES + 1)
        if len(blob) > MAX_BYTES: raise ValueError('Response resource bound exceeded')
    return json.loads(blob), blob

def failure(exc: Exception) -> dict:
    # Do not print exception messages, headers, request bodies, or token responses.
    return {'state': 'HOLD_ACCESS_OR_SOURCE', 'error_type': type(exc).__name__,
            'http_status': exc.code if isinstance(exc, urllib.error.HTTPError) else None}

def official_records(payload: dict, observed: datetime) -> list[dict]:
    if not isinstance(payload.get('incidents'), list): raise ValueError('Bad incident schema')
    result = []
    for item in payload['incidents'][:50]:
        iid = str(item.get('id', ''))
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', iid): continue
        result.append({'id': 'cloudflare:' + iid, 'source_type': 'PROVIDER_STATUS_REPORT',
            'url': 'https://www.cloudflarestatus.com/incidents/' + iid,
            'title': str(item.get('name', ''))[:240], 'reported_status': item.get('status'),
            'event_created_at': item.get('created_at'), 'event_updated_at': item.get('updated_at'),
            'retrieved_at': iso(observed), 'verification': 'PROVIDER_REPORTED_NOT_OUR_MEASUREMENT',
            'measured_delta': None, 'verified_savings_usd': None})
    return result

def reddit_records(payload: dict, observed: datetime) -> list[dict]:
    children = payload.get('data', {}).get('children')
    if not isinstance(children, list): raise ValueError('Bad listing schema')
    result = []
    terms = re.compile(r'outage|downtime|fail|latency|cost|billing|budget|recover|backup|update|slow|bottleneck|capacity', re.I)
    for child in children[:10]:
        item = child.get('data', {})
        if item.get('over_18') or item.get('is_self') is False: continue
        title = str(item.get('title', ''))[:240]
        if not terms.search(title): continue
        t = item.get('created_utc')
        if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t): continue
        created = datetime.fromtimestamp(t, timezone.utc)
        if not observed - timedelta(days=7) <= created <= observed + timedelta(minutes=5): continue
        iid = str(item.get('id', '')); sub = item.get('subreddit', '').lower()
        if sub not in SUBS or not re.fullmatch(r'[a-z0-9]{3,16}', iid): continue
        result.append({'id': 'reddit:' + iid, 'source_type': 'PUBLIC_USER_REPORT',
            'url': f'https://www.reddit.com/r/{sub}/comments/{iid}/', 'title': title,
            'event_created_at': iso(created), 'retrieved_at': iso(observed),
            'verification': 'UNVERIFIED_LEAD', 'reported_status': 'UNKNOWN',
            'measured_delta': None, 'verified_savings_usd': None})
    return result

def collect(out: Path, with_reddit: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=False)  # Never overwrite a prior capture.
    start = now(); records = []; receipts = {}
    try:
        payload, raw = request(CF)
        records += official_records(payload, start)
        (out / 'cloudflare_raw.json').write_bytes(raw)
        receipts['cloudflare'] = {'state': 'ACQUIRED_PROVIDER_REPORT', 'bytes': len(raw),
            'url': CF, 'raw_sha256': hashlib.sha256(raw).hexdigest()}
    except Exception as exc: receipts['cloudflare'] = failure(exc)
    receipts['reddit'] = {'state': 'NOT_REQUESTED'}
    if with_reddit:
        if not all(os.environ.get(k) for k in KEYS):
            receipts['reddit'] = {'state': 'HOLD_MISSING_RUNTIME_CREDENTIALS', 'rows': 0}
        else:
            try:
                client, secret, refresh = (os.environ[k] for k in KEYS)
                auth = base64.b64encode((client + ':' + secret).encode()).decode()
                token, _ = request('https://www.reddit.com/api/v1/access_token',
                    {'Authorization': 'Basic ' + auth},
                    urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh}).encode())
                access = token.get('access_token')
                if not isinstance(access, str) or not access: raise ValueError('No token')
                reads = []; found = []; errors = []
                for sub in SUBS:
                    try:
                        payload, raw = request(f'https://oauth.reddit.com/r/{sub}/new?limit=10&raw_json=1',
                            {'Authorization': 'Bearer ' + access})
                        batch = reddit_records(payload, start); found += batch
                        reads.append({'subreddit': sub, 'response_sha256': hashlib.sha256(raw).hexdigest(),
                                      'matched_rows': len(batch), 'raw_body_retained': False})
                    except Exception as exc: errors.append({'subreddit': sub, **failure(exc)})
                records += found
                receipts['reddit'] = {'state': 'ACQUIRED_BOUNDED_READ' if not errors else 'PARTIAL_HOLD',
                    'rows': len(found), 'reads': reads, 'errors': errors, 'authenticated_posting': False}
            except Exception as exc: receipts['reddit'] = {'rows': 0, **failure(exc)}
    dedup = {r['id']: r for r in records}
    report = {'schema_version': '1.0', 'captured_at': iso(start), 'sources': receipts,
        'records': list(dedup.values()), 'record_count': len(dedup),
        'source_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'ONE_BOUNDED_PASS_NO_BACKGROUND_MONITOR', 'economic_state': 'UNMEASURED',
        'performance_claim_allowed': False, 'secrets_saved': False}
    (out / 'ledger.json').write_bytes(canonical(report))
    files = [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(out.iterdir()) if p.is_file()]
    (out / 'SHA256_MANIFEST.json').write_bytes(canonical({'files': files,
        'hash_boundary': 'Checksums bind captured bytes; they do not prove reports true or savings realized.'}))
    return report

def paired_mae(rows: list[dict], protocol: dict) -> dict:
    """Score caller-provided replay rows; never manufacture performance from leads."""
    for key in ('dataset_sha256', 'protocol_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', protocol.get(key, '')): raise ValueError('Missing frozen identity')
    if protocol.get('metric') != 'MAE' or protocol.get('direction') != 'lower': raise ValueError('Metric required')
    if not rows: raise ValueError('No paired data')
    ids = []; b = []; c = []
    for r in rows:
        if not isinstance(r.get('target_id'), str) or not r['target_id']: raise ValueError('Target identity required')
        ids.append(r['target_id'])
        v = [r.get(k) for k in ('truth', 'baseline', 'candidate')]
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v):
            raise ValueError('Missing/non-finite outcome')
        b.append(abs(v[0] - v[1])); c.append(abs(v[0] - v[2]))
    if len(ids) != len(set(ids)): raise ValueError('Duplicate target')
    baseline = sum(b) / len(b); candidate = sum(c) / len(c)
    return {'pairs': len(rows), 'baseline_mae': baseline, 'candidate_mae': candidate,
        'mae_gain_pct': None if baseline == 0 else 100 * (baseline - candidate) / baseline,
        'status': 'DESCRIPTIVE_PAIRED_REPLAY_ONLY', 'protocol': protocol,
        'causal_savings_or_superiority_established': False, 'verified_savings_usd': None}

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--with-reddit', action='store_true'); a = ap.parse_args()
    report = collect(a.out, a.with_reddit)
    print(json.dumps({'record_count': report['record_count'],
        'source_states': {k: v['state'] for k, v in report['sources'].items()}, 'performance_claim_allowed': False}))

if __name__ == '__main__': main()
