"""Bounded public-source acquisition with immutable calibration hashes.
No secret, credentials or production mutation. Missing sources stay withheld.
"""
from __future__ import annotations
import argparse
import datetime as dt
import gzip
import hashlib
import json
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

STATIONS = ['41002','42001','44025','46042','46050','46237']
CAL_HASH = {
 '41002':'187185a0fc30bb0407760703239034427be331518051ca7e5192247138b04e8e',
 '42001':'c8f861736072838df8b49df88678525b6c75230449db311fa4a9193909e8fcf5',
 '44025':'f3cf85db2a0de9e7dbb08d46972474a9da10514da1ed7363d63d856bdfc741f6',
 '46042':'807a66353389c5acf74bdeeff2621d07ae46a190cdaa08f62f5306b8f5be63ab',
 '46050':'2c037515dda1c2ce2eccd2495afeeff324943cda5b9880465ebb6e2b8e824f55',
 '46237':'bee494e9d04428a46e05313a93cb3a0ec3ff0e46e0df28d001ef62acf5a0a416'}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--calibration-cache',type=Path)
    ap.add_argument('--expected',type=Path)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    expected={r['file']:r for r in json.loads(a.expected.read_text())['files']} if a.expected else {}
    records=[]
    for sid in STATIONS:
        for year in [2023,2025]:
            name=f'{sid}h{year}.txt.gz';path=a.out/name
            url=f'https://www.ndbc.noaa.gov/data/historical/stdmet/{name}'
            rec={'station':sid,'year':year,'file':name,'url':url,'auth':'public_no_key','status':'FAILED'}
            try:
                if name in expected and expected[name]['status']!='ACQUIRED':
                    rec.update(expected[name]);rec['replay_note']='original source hold retained without substitution'
                    path.unlink(missing_ok=True);records.append(rec);continue
                cached=a.calibration_cache/name if a.calibration_cache and year==2023 else None
                if cached and cached.exists():
                    data=cached.read_bytes()
                else:
                    data=None
                    for attempt in range(3):
                        try:
                            req=urllib.request.Request(url,headers={'User-Agent':'LumenCore-Research/Stage4 public-data benchmark'})
                            with urllib.request.urlopen(req,timeout=40) as r:
                                data=r.read(25*1024*1024+1)
                            if len(data)>25*1024*1024:raise ValueError('Size cap exceeded')
                            break
                        except urllib.error.HTTPError as e:
                            if e.code in [403,404] or attempt==2:raise
                            time.sleep(2)
                        except (TimeoutError,urllib.error.URLError):
                            if attempt==2:raise
                            time.sleep(2)
                if data is None:raise ValueError('Empty response')
                content=gzip.decompress(data)
                if not content.startswith(b'#YY') or b'WVHT' not in content.splitlines()[0] or b'APD' not in content.splitlines()[0]:
                    raise ValueError('Unexpected NDBC schema')
                sha=hashlib.sha256(data).hexdigest()
                wanted=CAL_HASH[sid] if year==2023 else expected.get(name,{}).get('sha256')
                if wanted and wanted!=sha:raise ValueError('Source changed; checksum mismatch')
                path.write_bytes(data)
                rec.update(status='ACQUIRED',sha256=sha,bytes=len(data))
            except Exception as e:
                path.unlink(missing_ok=True)
                rec['error']=type(e).__name__+': '+str(e)[:220]
            records.append(rec)
            print(name,rec['status'],flush=True)
    obj={'schema_version':'1.0','protocol_commit':'80bac1f947122c7c4753f7116d42163e07d3b9d2',
      'acquired_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'files':records,
      'expected_count':12,'acquired_count':sum(r['status']=='ACQUIRED' for r in records),
      'historical_not_live':True,'negative_and_missing_sources_retained':True}
    (a.out/'SOURCE_MANIFEST.json').write_text(json.dumps(obj,indent=2)+'\n')
    if a.expected:
        # Any previously available file that now cannot be reproduced fails replay.
        if any(r['status']!='ACQUIRED' and expected.get(r['file'],{}).get('status')=='ACQUIRED' for r in records):
            raise SystemExit('Frozen source replay failed')
    if obj['acquired_count']==0:raise SystemExit('No sources acquired')

if __name__=='__main__':main()
