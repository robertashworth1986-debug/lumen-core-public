from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wasserstein_distance

WINDOWS=[5,10,20,40,80,160]
HORIZONS=[20,60,120]

def mae(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    return float(np.mean(np.abs(a-b)))

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load_forge(path: Path) -> pd.DataFrame:
    raw=pd.read_excel(path,sheet_name=0,header=None)
    names=['time','p16b','flow16b1','flow16b2','temp16b','sep1','sep2','sep_total','p16a','pump_rate','liberty_p']
    d=raw.iloc[4:].copy(); d.columns=names
    d['time']=pd.to_datetime(d.time,errors='coerce')
    for c in names[1:]: d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
    cols=['sep_total','pump_rate','p16a','p16b','temp16b']; d[cols]=d[cols].ffill(limit=20)
    d=d[(d.sep_total.between(20,500)) & d.pump_rate.between(0,20) & d.p16a.between(0,5000) & d.p16b.between(0,3000) & d.temp16b.between(50,500)].copy().reset_index(drop=True)
    d['recovery_proxy']=d.sep_total/(d.pump_rate.replace(0,np.nan)*42.0)
    return d

def blocks(d: pd.DataFrame,h: int) -> pd.DataFrame:
    frame=pd.DataFrame({'time':d.time,'current':d.sep_total,'target':d.sep_total.shift(-h),'recovery':d.recovery_proxy,'temp':d.temp16b,'p16b':d.p16b})
    for w in WINDOWS: frame[f'rm{w}']=d.sep_total.rolling(w,min_periods=1).mean()
    frame=frame.dropna().reset_index(drop=True); n=len(frame); rows=[]
    for frac in np.arange(.40,.951,.05):
        ts=int(n*frac); te=int(n*min(frac+.05,.98)); vs=max(0,int(n*(frac-.15))); ve=max(vs+100,ts-h)
        val=frame.iloc[vs:ve]; test=frame.iloc[ts:te]
        best=min(WINDOWS,key=lambda w:mae(val.target,val[f'rm{w}']))
        mp=mae(test.target,test.current); mr=mae(test.target,test[f'rm{best}']); imp=100.0*(mp-mr)/mp
        r0=max(0,int(n*(frac-.15))); r1=max(0,int(n*(frac-.05))); r2=ts; ref=frame.iloc[r0:r1]; recent=frame.iloc[r1:r2]
        drift_parts={}
        for c in ['current','recovery','temp','p16b']:
            a=ref[c].dropna().to_numpy(float); b=recent[c].dropna().to_numpy(float); iqr=np.quantile(a,.75)-np.quantile(a,.25)
            drift_parts[c]=float(wasserstein_distance(a,b)/max(float(iqr),1e-9))
        rows.append({'start':str(test.time.iloc[0]),'end':str(test.time.iloc[-1]),'rolling_window':best,'rolling_improvement_pct':float(imp),'pre_drift_score':float(np.mean(list(drift_parts.values()))),'pre_drift_components':drift_parts})
    return pd.DataFrame(rows)

def online_rule(df: pd.DataFrame,min_history: int=4) -> dict:
    rows=[]
    for i in range(len(df)):
        threshold=None; use=False
        if i>=min_history:
            hist=df.iloc[:i]; vals=sorted(set(float(x) for x in hist.pre_drift_score))
            candidates=[min(vals)-1e-9]+vals; scored=[]
            for t in candidates:
                gain=np.where(hist.pre_drift_score.to_numpy(float)<=t,hist.rolling_improvement_pct.to_numpy(float),0.0)
                coverage=float(np.mean(hist.pre_drift_score.to_numpy(float)<=t))
                scored.append((float(np.mean(gain)),float(t),coverage))
            _,threshold,_=max(scored,key=lambda x:(x[0],-x[2])); use=bool(float(df.pre_drift_score.iloc[i])<=threshold)
        realized=float(df.rolling_improvement_pct.iloc[i]) if use else 0.0
        rows.append({'start':str(df.start.iloc[i]),'pre_drift_score':float(df.pre_drift_score.iloc[i]),'rolling_improvement_pct':float(df.rolling_improvement_pct.iloc[i]),'threshold':threshold,'use_rolling':use,'rule_improvement_pct':realized})
    r=pd.DataFrame(rows); post=r.iloc[min_history:]
    return {'warmup_blocks':min_history,'blocks':rows,'all_rolling_mean_improvement_pct':float(df.rolling_improvement_pct.mean()),'rule_mean_improvement_pct_all_blocks':float(r.rule_improvement_pct.mean()),'rule_mean_improvement_pct_post_warmup':float(post.rule_improvement_pct.mean()),'rule_worst_improvement_pct_post_warmup':float(post.rule_improvement_pct.min()),'rule_negative_blocks_post_warmup':int((post.rule_improvement_pct<0).sum()),'rule_coverage_post_warmup':float(post.use_rolling.mean())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--forge-xlsx',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    d=load_forge(args.forge_xlsx); result={'schema_version':'1.0','claim_boundary':'Offline forecast-model selection only. This is not a control rule, setpoint, safe operating limit, or external validation.','rows':len(d),'source_sha256':sha256_file(args.forge_xlsx),'horizons':{}}
    for h in HORIZONS:
        df=blocks(d,h); corr=float(spearmanr(df.pre_drift_score,df.rolling_improvement_pct).statistic)
        result['horizons'][str(h)]={'horizon_minutes':h/2.0,'block_count':len(df),'pre_drift_vs_gain_spearman':corr,'blocks':df.to_dict(orient='records'),'online_abstention':online_rule(df)}
    (args.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'ok','out':str(args.out/'summary.json')}))
if __name__=='__main__': main()
