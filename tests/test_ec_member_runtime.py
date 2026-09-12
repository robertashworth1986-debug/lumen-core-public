"""Member isolation, source boundaries, paper accounting and package custody."""
from __future__ import annotations
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import urllib.request
import urllib.error
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
import ec_member_runtime as rt

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

CATALOG=json.loads((ROOT/'dashboard/cohort/catalog.json').read_text(encoding='utf-8'))
PROFILE=next(c for c in CATALOG['companies'] if c['id']=='excalis')

def empty():return {'schema':rt.SCHEMA,'member':'excalis','items':[],'measurements':[],'grants':[],'scout':[],'care':[],'reviews':[],'paper':None}

def test_public_catalog_matches_exact_reviewed_roster_and_unknown_baselines():
    import csv
    with (ROOT/'docs/EC_COHORT_STRENGTH_RESEARCH_2026-09-11.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    assert len(CATALOG['companies'])==69
    assert {c['research_id'] for c in CATALOG['companies']}=={r['company_id'] for r in rows}
    assert len({c['id'] for c in CATALOG['companies']})==69
    assert all(len(c['hypotheses'])==3 for c in CATALOG['companies'])
    assert all(h['observed_value'] is None for c in CATALOG['companies'] for h in c['hypotheses'])

def test_workspace_isolation_and_approval_boundary():
    value=empty();assert rt.validate_workspace(value,'excalis') is value
    with pytest.raises(rt.UserError):rt.validate_workspace(value,'hopeconnect-health')
    value['items']=[{'id':'1','title':'Fictional brief','scope':'shape','acceptance':'designer check','revision':'1','stage':'in_progress','approved':False}]
    with pytest.raises(rt.UserError):rt.validate_workspace(value,'excalis')
    value['items'][0]['approved']=True
    rt.validate_workspace(value,'excalis')
    value['items'].append(dict(value['items'][0]))
    with pytest.raises(rt.UserError):rt.validate_workspace(value,'excalis')

def test_duplicate_and_nonfinite_json_rejected():
    for raw in [b'{"member":"a","member":"b"}',b'{"n":NaN}',b'{"n":Infinity}']:
        with pytest.raises(rt.UserError):rt.parse_json(raw)

def test_scout_reuses_relevance_helpers_without_inventing_eligibility():
    calls=[]
    def fetch(url,payload):
        calls.append((url,payload));return {'data':{'oppHits':[{'id':'12345','title':'Manufacturing research','agencyName':'Example agency','oppStatus':'posted'}]}},{'url':url,'retrieved_utc':'2026-09-12T00:00:00Z','sha256':'a'*64}
    result=rt.scout_grants(PROFILE,'manufacturing',fetch)
    assert len(calls)==1 and calls[0][0]=='https://api.grants.gov/v1/api/search2'
    assert result['opportunities'][0]['eligibility']=='UNVERIFIED'
    assert result['opportunities'][0]['url'].endswith('/12345')
    assert result['opportunities'][0]['relevance_score']>0
    with pytest.raises(rt.UserError):rt.scout_grants(PROFILE,'x',lambda *_:({'data':[]},{}))

def feed(epoch, *, stale=False, gap=False):
    end=int(epoch//3600)*3600
    rows=[[end-(21-i)*3600,95,150,100,100+i,20] for i in range(21)]
    if gap:rows.pop(15)
    def get(url,*_args,**_kwargs):
        if 'candles' in url:value=rows[::-1]
        else:value={'price':'121.25','time':rt.datetime.fromtimestamp(epoch-(600 if stale else 1),rt.timezone.utc).isoformat()}
        return value,{'url':url,'retrieved_utc':'2026-09-12T00:00:00Z','sha256':'a'*64}
    return get

def test_paper_tick_reconciles_costs_and_never_repeats_a_fill_for_same_candle():
    epoch=1789254000.3
    first=rt.paper_tick(None,feed(epoch),epoch)
    assert first['action']=='BUY'
    assert first['audit']['paper_fills']==1
    assert first['audit']['live_authorized'] is False
    assert first['audit']['broker_reconciled'] is False
    assert rt.Decimal(first['audit']['fees'])>0
    second=rt.paper_tick(first,feed(epoch+60),epoch+60)
    assert second['action']=='HOLD' and len(second['ledger']['events'])==1
    rt.audit_paper_ledger(second['ledger'])
    assert all('api.exchange.coinbase.com/products/BTC-USD/' in x['url'] for x in first['source_receipts'])

def test_paper_tick_holds_on_stale_quotes_and_missing_candles():
    epoch=1789254000.3
    with pytest.raises(rt.UserError,match='fresh'):rt.paper_tick(None,feed(epoch,stale=True),epoch)
    with pytest.raises(rt.UserError,match='history'):rt.paper_tick(None,feed(epoch,gap=True),epoch)

def test_ai_idempotency_and_local_audit_chain(tmp_path,monkeypatch):
    store=rt.Store(tmp_path/'member.sqlite3');runtime=rt.MemberRuntime(PROFILE,store);calls=[]
    monkeypatch.setattr(rt,'assistant_draft',lambda profile,prompt:calls.append(prompt) or {'text':'Working draft','status':'DRAFT_FOR_OWNER_REVIEW'})
    payload={'member':'excalis','request_id':'request-1','prompt':'Create a checklist.'}
    assert runtime.run('assistant',payload)==runtime.run('assistant',payload)
    assert len(calls)==1
    with pytest.raises(rt.UserError):runtime.run('assistant',{**payload,'prompt':'Different task'})
    with pytest.raises(rt.UserError):runtime.run('assistant',{**payload,'member':'other'})
    events=store.audit();previous='0'*64
    for e in events:
        assert e['previous']==previous
        assert e['hash']==rt.digest({k:e[k] for k in ('utc','kind','payload','previous')})
        previous=e['hash']
    assert 'Create a checklist.' not in json.dumps(events)

def test_schedule_rejects_ai_and_live_operations(tmp_path):
    r=rt.MemberRuntime(PROFILE,rt.Store(tmp_path/'s.sqlite3'))
    for k in ('assistant','live_order','grant_submit','email'):
        with pytest.raises(rt.UserError):r.schedule(k,True)
    assert r.schedule('paper',True)['paper']['interval_seconds']==3600
    assert r.schedule('paper',False)['paper']['enabled'] is False

def test_private_http_boundaries(tmp_path):
    public=tmp_path/'public';(public/'cohort').mkdir(parents=True);(public/'cohort/index.html').write_text('member workspace')
    runtime=rt.MemberRuntime(PROFILE,rt.Store(tmp_path/'private/store.sqlite3'))
    server=rt.ThreadingHTTPServer(('127.0.0.1',0),rt.make_handler(runtime,public))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with urllib.request.urlopen(base+'/api/member/status') as r:assert json.load(r)['member']=='excalis'
        for path,headers in [('/api/member/status',{'Host':'attacker.example'}),('/api/member/status',{'Origin':'https://attacker.example'}),('/.luma_data/store.sqlite3',{})]:
            with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(base+path,headers=headers))
        req=urllib.request.Request(base+'/api/member/workspace',data=json.dumps({'member':'excalis','workspace':empty()}).encode(),headers={'Content-Type':'application/json','X-Luma-Local':'1'})
        with urllib.request.urlopen(req) as r:assert json.load(r)['saved'] is True
        with urllib.request.urlopen(base+'/api/member/workspace') as r:assert json.load(r)['workspace']['member']=='excalis'
        req=urllib.request.Request(base+'/api/member/workspace',data=b'{}',headers={'Content-Type':'application/json'})
        with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(req)
    finally:server.shutdown();server.server_close();thread.join(timeout=2)

def test_all_69_archives_are_bounded_scoped_and_hash_verified():
    downloads=ROOT/'dashboard/cohort/downloads';manifest=json.loads((downloads/'manifest.json').read_text())
    assert len(manifest['packages'])==69
    for entry in manifest['packages']:
        raw=(downloads/entry['file']).read_bytes()
        assert len(raw)==entry['bytes']<3_000_000
        assert hashlib.sha256(raw).hexdigest()==entry['sha256']
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=z.namelist();assert len(names)==len(set(names))
            assert all(not n.startswith(('/','\\')) and '..' not in Path(n).parts and '\\' not in n for n in names)
            assert all((i.external_attr>>16)&0o170000==0o100000 for i in z.infolist())
            assert not any('.env' in n or 'sqlite' in n or 'PRIVATE_CONTEXT' in n for n in names)
            own=json.loads(z.read('public/cohort/catalog.json'))
            assert len(own['companies'])==1 and own['companies'][0]['id']==entry['member']
            pm=json.loads(z.read('package-manifest.json'));assert pm['member']==entry['member']
            for f in pm['files']:
                b=z.read(f['path']);assert len(b)==f['bytes'];assert hashlib.sha256(b).hexdigest()==f['sha256']
            assert {f['path'] for f in pm['files']}==set(names)-{'package-manifest.json'}
