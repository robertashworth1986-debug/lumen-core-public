from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
import operator_feed_reads as feeds
from operator_api_access import OperatorApiAccessMiddleware

NOW = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)
STAMP = NOW.isoformat()
RUN = NOW.strftime('%Y%m%dT%H%M%SZ')

class FeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {feeds.ENV_PREFIX + f.upper(): '300' for f in feeds.FEEDS}

    def put(self, path, obj):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(obj))
        return dest

    def heartbeat(self, **overrides):
        return self.put('out/execution/live_executor_heartbeat.json',
                        {'schema_version':'1.0.0', 'timestamp_utc':STAMP, 'status':'blocked', **overrides})

    def evidence(self):
        prefix = f'dashboard/evidence/runs/{RUN}/'
        p = self.put(prefix+'summary.json', {'run_utc':RUN,'n_datasets_succeeded':1,'n_datasets_in_universe':2, 'private_extra':'secret-not-to-return'})
        self.put(prefix+'manifest.sha256.json', {'run_utc':RUN,'files':{'summary.json':hashlib.sha256(p.read_bytes()).hexdigest()}})
        return p

    def observe(self, name='executor_heartbeat', **kwargs):
        return feeds.observe(name, self.root, environ=kwargs.pop('environ',self.env), now=NOW, **kwargs)

    def reason(self, expected, name='executor_heartbeat', **kwargs):
        status, result = self.observe(name, **kwargs)
        self.assertEqual(status,503)
        self.assertFalse(result['data_available'])
        self.assertIsNone(result['data'])
        self.assertEqual(result['disposition'],expected)
        return result

    def test_unmapped_never_reads(self):
        with patch.object(feeds.ArtifactReader,'object',side_effect=AssertionError):
            self.reason('producer_unmapped','live_status')

    def test_missing_budget_never_reads(self):
        with patch.object(feeds.ArtifactReader,'object',side_effect=AssertionError):
            self.reason('freshness_unconfigured', environ={})

    def test_invalid_budgets(self):
        for budget in ['0','-1','nan','inf','1e999','garbage']:
            with self.subTest(budget=budget):
                self.reason('freshness_unconfigured',environ={feeds.ENV_PREFIX+'EXECUTOR_HEARTBEAT':budget})

    def test_missing(self): self.reason('source_missing')

    def test_exact_age_boundary_is_accepted(self):
        self.heartbeat(timestamp_utc=(NOW-timedelta(seconds=300)).isoformat())
        self.assertEqual(self.observe()[0],200)

    def test_detected_concurrent_change_is_rejected(self):
        from types import SimpleNamespace
        self.heartbeat()
        original = os.fstat
        calls = 0
        def changing(fd):
            nonlocal calls
            calls += 1
            info = original(fd)
            if calls == 2:
                return SimpleNamespace(st_size=info.st_size, st_mtime_ns=info.st_mtime_ns+1, st_ctime_ns=info.st_ctime_ns)
            return info
        with patch.object(feeds.os,'fstat',side_effect=changing):
            self.reason('source_changed_during_read')

    def test_inventory_limit_fails_closed(self):
        self.evidence()
        (self.root/'dashboard/evidence/runs/unrecognized').mkdir()
        with patch.object(feeds,'MAX_RUNS',1):
            self.reason('source_inventory_oversized','evidence_summary')

    def test_heartbeat_allowlist_and_no_writes(self):
        p=self.heartbeat(account_balance=123, private_extra='secret-not-to-return')
        before=(p.read_bytes(),p.stat().st_mtime_ns)
        with patch('subprocess.run',side_effect=AssertionError), patch('socket.socket',side_effect=AssertionError):
            status, result = self.observe()
        self.assertEqual(status,200)
        self.assertEqual(result['data']['status'],'blocked')
        self.assertNotIn('secret-not-to-return',json.dumps(result))
        self.assertEqual(set(result['data']), {'schema_version','status','timestamp_utc'})
        self.assertEqual(before,(p.read_bytes(),p.stat().st_mtime_ns))
        self.assertEqual(result['source_sha256'],hashlib.sha256(p.read_bytes()).hexdigest())

    def test_timestamp_failures(self):
        for stamp, reason in [(None,'source_timestamp_missing'),('bad','source_timestamp_invalid'),('2026-10-27T18:00:00','source_timestamp_invalid'),((NOW+timedelta(seconds=1)).isoformat(),'source_timestamp_future'),((NOW-timedelta(seconds=301)).isoformat(),'source_stale')]:
            with self.subTest(stamp=stamp):
                self.heartbeat(timestamp_utc=stamp)
                self.reason(reason)

    def test_schema_failures(self):
        for values in [{'schema_version':'2'}, {'status':None}, {'status':'private/path?secret'}, {'status':True}, {'status':'credentialLikePrivateText'}]:
            with self.subTest(values=values):
                self.heartbeat(**values);self.reason('invalid_schema')

    def test_strict_json(self):
        p=self.heartbeat()
        for raw in ['[]','{}','{"x":1,"x":2}','{"x":NaN}','{"x":1e999}','not-json']:
            with self.subTest(raw=raw):
                p.write_text(raw)
                status, result=self.observe()
                self.assertEqual(status,503)
                self.assertIn(result['disposition'], {'invalid_schema','invalid_json'})

    def test_oversized(self):
        self.heartbeat().write_bytes(b' '*(feeds.MAX_BYTES+1))
        self.reason('source_oversized')

    def test_file_symlink(self):
        p=self.heartbeat();p.unlink();p.symlink_to('/etc/passwd')
        self.reason('source_unreadable_or_unsafe')

    def test_parent_symlink(self):
        outside=self.root/'outside';outside.mkdir()
        (self.root/'out').symlink_to(outside,target_is_directory=True)
        self.reason('source_unreadable_or_unsafe')

    def test_configured_root_symlink(self):
        self.heartbeat(); alias=self.root/'alias';alias.symlink_to(self.root,target_is_directory=True)
        status,result=feeds.observe('executor_heartbeat',alias,environ=self.env,now=NOW)
        self.assertEqual(status,503)

    def test_path_escape_rejected(self):
        for path in ['../secret','/etc/passwd']:
            with self.assertRaises(feeds.Unavailable):feeds.ArtifactReader(self.root).raw(path)

    def test_fifo_never_blocks(self):
        p=self.heartbeat();p.unlink();os.mkfifo(p)
        self.reason('unsafe_source')

    def test_valid_evidence_hash_bound_allowlist(self):
        self.evidence();status,result=self.observe('evidence_summary')
        self.assertEqual(status,200)
        self.assertEqual(result['data']['n_datasets_succeeded'],1)
        self.assertNotIn('private_extra',json.dumps(result))
        self.assertEqual(result['data']['evidence_type'],'retained_research_run')

    def test_evidence_hash_mismatch(self):
        p=self.evidence();p.write_text(p.read_text()+' ')
        self.reason('provenance_mismatch','evidence_summary')

    def test_evidence_manifest_missing(self):
        p=self.evidence();(p.parent/'manifest.sha256.json').unlink()
        self.reason('source_missing','evidence_summary')

    def test_evidence_symlink_run(self):
        runs=self.root/'dashboard/evidence/runs';runs.mkdir(parents=True)
        (runs/RUN).symlink_to(self.root,target_is_directory=True)
        self.reason('unsafe_source','evidence_summary')

    def test_evidence_stale(self):
        self.evidence()
        env={feeds.ENV_PREFIX+'EVIDENCE_SUMMARY':'1'}
        status,result=feeds.observe('evidence_summary',self.root,environ=env,now=NOW+timedelta(seconds=2))
        self.assertEqual((status,result['disposition']),(503,'source_stale'))

    def test_federal_generated_time_does_not_prove_sources(self):
        self.put('out/federal_brief.json',{'generated_utc':STAMP,'portfolio':{},'financial_impact':{}})
        self.reason('source_provenance_unverified','federal_brief')

    @unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"), "FastAPI/httpx integration dependencies unavailable")
    def test_every_route_auth_before_reads_and_no_store(self):
        from fastapi import FastAPI
        import httpx
        app=FastAPI()
        feeds.install_private_feed_routes(app,self.root)
        feeds.install_private_feed_routes(app,self.root) # repeat facade imports
        token='synthetic-private-feed-test-token-0000'
        app.add_middleware(OperatorApiAccessMiddleware,token_provider=lambda:(token,))
        async def run():
            transport=httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport,base_url='http://test') as client:
                with patch.object(feeds,'observe',side_effect=AssertionError):
                    for name in feeds.FEEDS:
                        for headers in ({}, {'Authorization':'Bearer incorrect-token'}):
                            response=await client.get('/api/'+name+'.json',headers=headers)
                            self.assertEqual(response.status_code,401)
                for name in feeds.FEEDS:
                    response=await client.get('/api/'+name+'.json',headers={'Authorization':'Bearer '+token})
                    self.assertEqual(response.status_code,503)
                    self.assertEqual(response.headers['cache-control'],'no-store')
                    self.assertFalse(response.json()['data_available'])
        asyncio.run(run())

    @unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"), "FastAPI/httpx integration dependencies unavailable")
    def test_minimal_profile_does_not_import_reader_or_legacy(self):
        import subprocess
        code = Path(__file__).resolve().parents[1] / 'code'
        script = r"""
import asyncio, sys, httpx
import luma_experience_gateway as gateway
assert 'operator_feed_reads' not in sys.modules
assert 'luma_experience_gateway_legacy' not in sys.modules
async def check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app),base_url='http://test') as client:
        for name in ('live_status','federal_brief','evidence_summary','executor_heartbeat'):
            response = await client.get('/api/'+name+'.json',headers={'Authorization':'Bearer synthetic-minimal-private-feed-token'})
            assert response.status_code == 503
            assert response.json()['detail'] == 'operator components remain HOLD in minimal reviewer profile'
        assert (await client.get('/health')).status_code == 200
asyncio.run(check())
"""
        env = {**os.environ, 'PYTHONPATH': str(code), 'LUMA_GATEWAY_SERVING_PROFILE':'minimal',
               'LUMA_OPERATOR_API_TOKEN':'synthetic-minimal-private-feed-token', 'LUMA_OPERATOR_API_TOKENS':''}
        result = subprocess.run([sys.executable,'-c',script],env=env,cwd=self.root,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(list(self.root.iterdir()), [])

    @unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("fastapi", "httpx", "requests")), "Full HTTP integration dependencies unavailable")
    def test_real_operator_facade_routes_auth_and_repeat_import(self):
        import subprocess
        code = Path(__file__).resolve().parents[1] / 'code'
        script = r"""
import sys, os
sys.dont_write_bytecode = True
def audit(event, args):
    if event in {'socket.connect', 'subprocess.Popen', 'os.system'}:
        raise RuntimeError('external effect blocked by test')
sys.addaudithook(audit)
import luma_experience_gateway as gateway
from operator_feed_reads import FEEDS
import importlib
importlib.reload(gateway)
for name in FEEDS:
    assert sum(getattr(route, 'path', None) == '/api/'+name+'.json' for route in gateway.app.routes) == 1
import asyncio, httpx
async def check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app),base_url='http://test') as client:
        for name in FEEDS:
            path = '/api/'+name+'.json'
            assert (await client.get(path)).status_code == 401
            response = await client.get(path, headers={'Authorization':'Bearer synthetic-real-legacy-private-feed-token'})
            assert response.status_code == 503
            assert response.json()['schema'] == 'lumencore_private_feed_observation.v1'
asyncio.run(check())
"""
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(code), os.environ.get('PYTHONPATH','')]),
               'LUMA_GATEWAY_SERVING_PROFILE':'operator', 'LUMA_STACK_ROOT':str(self.root),
               'LUMA_DASHBOARD_DIR':str(self.root/'dashboard'),
               'LUMA_OPERATOR_API_TOKEN':'synthetic-real-legacy-private-feed-token', 'LUMA_OPERATOR_API_TOKENS':''}
        for name in feeds.FEEDS:
            env.pop(feeds.ENV_PREFIX+name.upper(),None)
        result = subprocess.run([sys.executable,'-c',script],env=env,cwd=self.root,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
