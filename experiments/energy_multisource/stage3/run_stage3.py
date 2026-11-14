"""Exact-time, separate-year energy replication. Offline research, not control.
Read-only raw XLSX parser uses stdlib XML; no workbook recalculation or edits.
Run: python run_stage3.py --prior PRIOR_BUNDLE_DIR --history HISTORY_DIR --out RESULTS
"""
from __future__ import annotations
import argparse, csv, datetime as dt, gzip, hashlib, json, math, platform, sys
import xml.etree.ElementTree as ET
from pathlib import Path
import zipfile
import numpy as np

DAY = 86400
SEED = 20260905
PROTOCOL_COMMIT = 'c33f86e999268169dcd6ddd2b8eb06680e1d99c6'
STATIONS = ['41002','42001','44025','46042','46050','46237']

def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def jwrite(p: Path, obj: object) -> None:
    p.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')

def valid(x: np.ndarray) -> np.ndarray:
    return np.isfinite(x) & (x >= 0)

def xlsx_forge(path: Path) -> tuple[np.ndarray, np.ndarray]:
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    rows = []
    with zipfile.ZipFile(path) as z:
        with z.open('xl/worksheets/sheet1.xml') as f:
            for _, e in ET.iterparse(f, events=('end',)):
                if e.tag != ns + 'row': continue
                if int(e.attrib['r']) > 4:
                    a = [float('nan')] * 11
                    for c in e:
                        letters = ''.join(k for k in c.attrib.get('r', '') if k.isalpha())
                        n = 0
                        for k in letters: n = n * 26 + ord(k) - 64
                        v = c.find(ns + 'v')
                        if 1 <= n <= 11 and v is not None and c.attrib.get('t') not in ('s','e'):
                            try: a[n - 1] = float(v.text)
                            except (TypeError, ValueError): pass
                    if np.isfinite(a[0]): rows.append(a)
                e.clear()
    a = np.asarray(rows, dtype=float)
    t = np.rint((a[:, 0] - 25569.) * DAY).astype(np.int64)
    o = np.argsort(t); t = t[o]; a = a[o]
    if np.any(np.diff(t) <= 0): raise ValueError('Duplicate FORGE timestamps')
    return t, a

def ffill_limit(x: np.ndarray, limit: int) -> np.ndarray:
    idx = np.where(np.isfinite(x), np.arange(len(x)), -1)
    last = np.maximum.accumulate(idx)
    good = (last >= 0) & (np.arange(len(x)) - last <= limit)
    z = x.copy(); z[good] = x[last[good]]
    return z

def legacy_audit(t: np.ndarray, a: np.ndarray) -> dict:
    z = a.copy()
    for c in (7,9,8,1,4): z[:,c] = ffill_limit(z[:,c],20)
    m = np.ones(len(t),dtype=bool)
    for c,lo,hi in [(7,20,500),(9,0,20),(8,0,5000),(1,0,3000),(4,50,500)]:
        m &= (z[:,c]>=lo)&(z[:,c]<=hi)
    tt = t[m]; raw = a[m,7]; out = {}
    for h in (20,60,120):
        elapsed = tt[h:]-tt[:-h]
        out[str(h//2)] = {'pairs':len(elapsed), 'incorrect_elapsed_horizon_pairs':int(np.sum(elapsed!=h*30)),
          'incorrect_elapsed_horizon_fraction':float(np.mean(elapsed!=h*30)),
          'max_actual_horizon_minutes':float(elapsed.max()/60),
          'forward_filled_future_target_pairs':int(np.sum(~np.isfinite(raw[h:])))}
    return {'raw_rows':len(t),'legacy_retained_rows':int(m.sum()),'retained_imputed_flow_cells':int(np.sum(~np.isfinite(raw))),
      'horizons_minutes':out,
      'method_defects':['Filtering rows before shifting changes elapsed-time horizons across gaps.',
        'The earlier next-stage validation selection did not purge targets crossing its test boundary.',
        'The earlier drift gate used the preceding whole block score before all its horizon-delayed outcomes were available.',
        'Earlier flow targets could include forward-filled measurements.',
        'Repeated analysis of this FORGE record is exploratory, not an untouched confirmation.']}

def read_ndbc(path: Path, expected_year: int) -> tuple[np.ndarray,np.ndarray,dict]:
    text = gzip.decompress(path.read_bytes()).decode('ascii')
    lines = text.splitlines(); cols = lines[0].lstrip('#').split()
    iy, ip = cols.index('WVHT'), cols.index('APD'); times=[]; vals=[]; missing=0
    for line in lines[1:]:
        if not line.strip() or line.startswith('#'): continue
        v = line.split()
        if len(v)<len(cols): raise ValueError('Truncated NDBC row')
        y,mo,d,h,mi = map(int,v[:5])
        if y != expected_year: raise ValueError('NDBC source year mismatch')
        stamp=int(dt.datetime(y,mo,d,h,mi,tzinfo=dt.timezone.utc).timestamp())
        try: hs,p = float(v[iy]),float(v[ip])
        except ValueError: hs,p = float('nan'),float('nan')
        ok = np.isfinite(hs) and np.isfinite(p) and 0<=hs<99 and 0<p<99
        times.append(stamp); vals.append(hs*hs*p if ok else float('nan')); missing+=int(not ok)
    t=np.asarray(times,np.int64); x=np.asarray(vals,float); o=np.argsort(t); t=t[o]; x=x[o]
    if np.any(np.diff(t)<=0): raise ValueError('Duplicate NDBC timestamps')
    return t,x,{'file':path.name,'sha256':digest(path),'raw_rows':len(t),'valid_proxy_rows':int(valid(x).sum()),'missing_or_sentinel_rows':missing}

def issue_indices(t: np.ndarray, x: np.ndarray, stride: int) -> np.ndarray:
    ans=[]; last=-10**18
    for i in np.flatnonzero(valid(x)):
        if t[i]-last>=stride: ans.append(i); last=int(t[i])
    return np.asarray(ans,dtype=int)

def rolling(t: np.ndarray,x: np.ndarray,at: np.ndarray,w: int,cadence: float) -> np.ndarray:
    ok=valid(x); s=np.r_[0.,np.cumsum(np.where(ok,x,0.))]; c=np.r_[0,np.cumsum(ok)]
    left=np.searchsorted(t,at-w,side='right'); right=np.searchsorted(t,at,side='right')
    n=c[right]-c[left]; ans=np.full(len(at),np.nan)
    enough=(n>=max(1,math.ceil(.8*w/cadence)))&(at>=t[0]+w)
    ans[enough]=(s[right[enough]]-s[left[enough]])/n[enough]
    return ans

def exact_target(t: np.ndarray,x: np.ndarray,at: np.ndarray,h: int) -> np.ndarray:
    k=np.searchsorted(t,at+h); ans=np.full(len(at),np.nan)
    ok=k<len(t); j=np.flatnonzero(ok); exact=t[k[j]]==at[j]+h; j=j[exact]
    good=valid(x[k[j]]); j=j[good]; ans[j]=x[k[j]]
    return ans

def conservative_gate(at: np.ndarray,target: np.ndarray,p: np.ndarray,r: np.ndarray,h: int) -> np.ndarray:
    """Past error heuristic. Strictly exclude incomplete days and unmatured labels."""
    day=at//DAY; first=int(day.min()); nd=int(day.max()-first+1); ix=day-first
    ok=np.isfinite(target)&np.isfinite(p)&np.isfinite(r)
    cnt=np.bincount(ix[ok],minlength=nd); possible=np.bincount(ix,minlength=nd)
    ps=np.bincount(ix[ok],weights=np.abs(target[ok]-p[ok]),minlength=nd)
    rs=np.bincount(ix[ok],weights=np.abs(target[ok]-r[ok]),minlength=nd)
    flags=np.zeros(len(at),bool); cache={}
    for i in range(len(at)):
        last=int((at[i]-h-1)//DAY-1-first)
        if last not in cache:
            hist=np.arange(max(0,last-6),min(nd,last+1))
            hist=hist[(cnt[hist]>0)&(cnt[hist]>=.8*possible[hist])]
            use=False
            if len(hist)>=5:
                daily=(ps[hist]-rs[hist])/cnt[hist]
                se=float(np.std(daily,ddof=1)/math.sqrt(len(daily)))
                pooled=(ps[hist].sum()-rs[hist].sum())/max(ps[hist].sum(),1e-15)
                use=bool(pooled>=.05 and daily.mean()>1.96*se)
            cache[last]=use
        flags[i]=cache[last] and np.isfinite(r[i])
    return flags

def boot_compare(at: np.ndarray,truth: np.ndarray,base: np.ndarray,cand: np.ndarray,block: int,seed: int) -> dict:
    eb=np.abs(truth-base); ec=np.abs(truth-cand)
    di=at//DAY; di=di-di.min(); nday=int(di.max()+1)
    counts=np.bincount(di,minlength=nday); bs=np.bincount(di,weights=eb,minlength=nday); cs=np.bincount(di,weights=ec,minlength=nday)
    mb=float(eb.mean()); mc=float(ec.mean()); nonempty=counts>0
    result={'n':len(eb),'calendar_days':nday,'scored_days':int(nonempty.sum()),'baseline_mae':mb,'candidate_mae':mc,
      'baseline_p95_absolute_error':float(np.quantile(eb,.95)), 'candidate_p95_absolute_error':float(np.quantile(ec,.95)),
      'worse_days':int(np.sum(cs[nonempty]>bs[nonempty]+1e-12))}
    if mb<=1e-12 or nonempty.sum()<5:
        result.update(improvement_pct=None,ci95_pct=None,p_one_sided=1.,status='INSUFFICIENT_EVIDENCE'); return result
    result['improvement_pct']=100*(mb-mc)/mb
    rng=np.random.default_rng(seed); B=10000
    starts=rng.integers(0,nday,size=(B,math.ceil(nday/block)))
    indices=((starts[:,:,None]+np.arange(block))%nday).reshape(B,-1)[:,:nday]
    bt=bs[indices].sum(axis=1); ct=cs[indices].sum(axis=1); nt=counts[indices].sum(axis=1)
    good=(bt>1e-12)&(nt>0)
    gain=100*(bt[good]-ct[good])/bt[good]
    delta=mb-mc
    null_delta=(bt[good]-ct[good]-delta*nt[good])/nt[good]
    result['ci95_pct']=[float(v) for v in np.quantile(gain,[.025,.975])]
    result['p_one_sided']=float((np.sum(null_delta>=delta)+1)/(len(null_delta)+1))
    result['status']='SCORED'; result['resampling']='paired circular moving calendar-day blocks; heuristic under nonstationarity'
    return result

def evaluate(name: str,t: np.ndarray,x: np.ndarray,cut: int,end: int,horizons: list[int],windows: list[int],stride: int,block: int) -> list[dict]:
    ii=issue_indices(t,x,stride); at=t[ii]; p=x[ii]
    cal_times=t[(t<cut)&valid(x)]; cadence=float(np.median(np.diff(cal_times)))
    if not np.isfinite(cadence) or cadence<=0: raise ValueError('Invalid calibration cadence')
    rm={w:rolling(t,x,at,w,cadence) for w in windows}; res=[]
    for hi,h in enumerate(horizons):
        target=exact_target(t,x,at,h)
        cal=(at+h<cut)&np.isfinite(target)
        cal &= np.logical_and.reduce([np.isfinite(v) for v in rm.values()])
        if cal.sum()<100: raise ValueError('Too few complete calibration pairs')
        w=min(windows,key=lambda w:(float(np.abs(target[cal]-rm[w][cal]).mean()),w))
        r=rm[w]; flags=conservative_gate(at,target,p,r,h); gate=np.where(flags,r,p)
        scheduled=(at>=cut)&(at+h<end)
        common=scheduled&np.isfinite(target)&np.isfinite(r)&np.isfinite(p)
        if common.sum()<100: raise ValueError('Too few complete evaluation pairs')
        for ci,(method,b,c) in enumerate([('rolling_vs_persistence',p,r),('gate_vs_persistence',p,gate),('gate_vs_rolling',r,gate)]):
            v=boot_compare(at[common],target[common],b[common],c[common],block,SEED+hi*10+ci)
            v.update(dataset=name,horizon_minutes=h/60,comparison=method,selected_window_minutes=w/60,
              calibration_pairs=int(cal.sum()), calibration_last_target=str(np.datetime64(int((at[cal]+h).max()),'s')),
              evaluation_start=str(np.datetime64(int(cut),'s')),evaluation_end_exclusive=str(np.datetime64(int(end),'s')),
              eligible_origin_count=int(scheduled.sum()), common_pair_coverage=float(common.sum()/scheduled.sum()),
              gate_rolling_fraction=float(flags[common].mean()),cadence_minutes=cadence/60,
              exposure='previously_examined_FORGE_exploratory' if name=='FORGE1683' else 'separate_2024_year_calibrated_on_2023')
            res.append(v)
    return res

def holm(rows: list[dict]) -> None:
    order=sorted(range(len(rows)),key=lambda i:rows[i]['p_one_sided']); running=0.
    for rank,i in enumerate(order):
        r=rows[i]; running=max(running,min(1.,r['p_one_sided']*(63-rank))); r['holm_p']=running
        passes=r.get('improvement_pct') is not None and r['improvement_pct']>=5 and r.get('ci95_pct') and r['ci95_pct'][0]>0 and running<.05
        r['screen_pass']=bool(passes)
        r['independent_validation']=False
        r['confirmation_status']='EXPLORATORY_ONLY' if r['dataset']=='FORGE1683' else ('SEPARATE_YEAR_SCREEN_PASS' if passes else 'HOLD_OR_NEGATIVE')

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument('--prior',type=Path,required=True); ap.add_argument('--history',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True); scores=[]; failures=[]; sources=[]
    p=next((a.prior/'raw/forge1683').rglob('*30 sec increment*.xlsx'))
    t,z=xlsx_forge(p); audit=legacy_audit(t,z); jwrite(a.out/'integrity_audit.json',audit)
    sources.append({'file':str(p),'sha256':digest(p),'rows':len(t),'state':'raw_uncorrected_field_measurements','timezone':'source local clock, timezone unspecified; no cross-source joins'})
    cut=int(t[0]+.4*(t[-1]-t[0])); end=int(t[-1]+1)
    scores.extend(evaluate('FORGE1683',t,z[:,7],cut,end,[600,1800,3600],[150,300,600,1200,2400,4800],300,3))
    for sid in STATIONS:
        try:
            x1,y1,m1=read_ndbc(a.history/(sid+'h2023.txt.gz'),2023); x2,y2,m2=read_ndbc(a.history/(sid+'h2024.txt.gz'),2024)
            sources.extend([m1,m2]); t=np.r_[x1,x2]; y=np.r_[y1,y2]
            cut=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()); end=int(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc).timestamp())
            scores.extend(evaluate('NDBC_'+sid,t,y,cut,end,[3600,10800,21600],[3600,7200,10800,21600],1800,7))
        except Exception as e:
            failures.append({'station':sid,'status':'FAILED_NOT_PROMOTED','error':type(e).__name__+': '+str(e)[:300]})
    holm(scores)
    summary={'experiment':'stage3_exact_time_separate_year_replication','protocol_commit':PROTOCOL_COMMIT,
      'runtime_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'versions':{'python':platform.python_version(),'numpy':np.__version__},
      'claim_boundary':'Internal offline research. No operation changes, independent validation, or measured energy savings. Moving averages are standard baselines. Reused FORGE data cannot be confirmatory.',
      'comparisons_expected':63,'comparisons_scored':len(scores),'acquisition_or_analysis_failures':failures,'sources':sources,'scores':scores,
      'uncertainty_limits':'Moving-block resampling assumes sufficient weak dependence and stability. Confidence intervals are not safety guarantees. There is only one FORGE test campaign.'}
    jwrite(a.out/'summary.json',summary)
    if scores:
        fields=list(scores[0])
        with (a.out/'comparisons.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(scores)
    jwrite(a.out/'SHA256_MANIFEST.json',{'files':[{'path':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(a.out.iterdir()) if p.is_file() and p.name!='SHA256_MANIFEST.json']})
    print(json.dumps({'scored':len(scores),'failures':failures,'out':str(a.out)}))
if __name__=='__main__': main()
