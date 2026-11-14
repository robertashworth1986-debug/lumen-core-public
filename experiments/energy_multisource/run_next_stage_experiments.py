from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance, spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED=42
WINDOWS=[5,10,20,40,80,160]
RHO=1025.0
G=9.80665
WAVE_KW_M=RHO*G*G/(64*math.pi)/1000.0

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()

def load_forge1683(path: Path) -> pd.DataFrame:
    raw=pd.read_excel(path,sheet_name=0,header=None)
    names=['time','p16b','flow16b1','flow16b2','temp16b','sep1','sep2','sep_total','p16a','pump_rate','liberty_p']
    d=raw.iloc[4:].copy(); d.columns=names
    d['time']=pd.to_datetime(d['time'],errors='coerce')
    for c in names[1:]: d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['time']).sort_values('time').reset_index(drop=True)
    cols=['sep_total','pump_rate','p16a','p16b','temp16b']; d[cols]=d[cols].ffill(limit=20)
    d=d[(d['sep_total'].between(20,500)) & (d['pump_rate'].between(0,20)) & d['p16a'].between(0,5000) & d['p16b'].between(0,3000) & d['temp16b'].between(50,500)].copy()
    d=d.sort_values('time').reset_index(drop=True)
    d['recovery_proxy']=d['sep_total']/(d['pump_rate'].replace(0,np.nan)*42.0)
    return d

def forge_walkforward(d: pd.DataFrame) -> dict:
    out={}
    for h in [20,60,120]:
        frame=pd.DataFrame({'time':d.time,'current':d.sep_total,'target':d.sep_total.shift(-h)})
        for w in WINDOWS: frame[f'rm{w}']=d.sep_total.rolling(w,min_periods=1).mean()
        frame['vol20']=d.sep_total.diff().abs().rolling(20,min_periods=5).mean(); frame['ramp20']=(d.sep_total-d.sep_total.shift(20)).abs()
        frame=frame.dropna().reset_index(drop=True); n=len(frame); folds=[]
        for frac in [.55,.65,.75,.85]:
            ts=int(n*frac); te=int(n*min(frac+.10,.95)); vs=max(0,int(n*(frac-.15))); ve=ts
            val=frame.iloc[vs:ve]; test=frame.iloc[ts:te]
            best=min(WINDOWS,key=lambda w:mean_absolute_error(val.target,val[f'rm{w}']))
            best_cfg=None
            for metric in ['vol20','ramp20']:
                for q in [.4,.5,.6,.7,.8,.9,.95]:
                    thr=float(val[metric].quantile(q)); pred=np.where(val[metric].values<=thr,val[f'rm{best}'].values,val.current.values); mae=mean_absolute_error(val.target,pred)
                    if best_cfg is None or mae<best_cfg['val_mae']: best_cfg={'metric':metric,'q':q,'threshold':thr,'val_mae':float(mae)}
            pred_roll=test[f'rm{best}'].values; pred_gate=np.where(test[best_cfg['metric']].values<=best_cfg['threshold'],pred_roll,test.current.values)
            mp=mean_absolute_error(test.target,test.current); mr=mean_absolute_error(test.target,pred_roll); mg=mean_absolute_error(test.target,pred_gate)
            folds.append({'test_start':str(test.time.iloc[0]),'test_end':str(test.time.iloc[-1]),'window':best,'gate':best_cfg,'n_test':len(test),'persistence_mae':float(mp),'rolling_improvement_pct':float(100*(mp-mr)/mp),'gated_improvement_pct':float(100*(mp-mg)/mp),'gate_roll_fraction':float(np.mean(test[best_cfg['metric']].values<=best_cfg['threshold']))})
        out[str(h)]={'horizon_minutes':h/2.0,'folds':folds,'mean_rolling_improvement_pct':float(np.mean([f['rolling_improvement_pct'] for f in folds])),'mean_gated_improvement_pct':float(np.mean([f['gated_improvement_pct'] for f in folds])),'negative_rolling_folds':int(sum(f['rolling_improvement_pct']<0 for f in folds))}
    return out

def forge_sensor_robustness(d: pd.DataFrame) -> dict:
    out={}
    for h in [20,60,120]:
        frame=pd.DataFrame({'current':d.sep_total,'target':d.sep_total.shift(-h)})
        for w in WINDOWS: frame[f'rm{w}']=d.sep_total.rolling(w,min_periods=1).mean()
        frame=frame.dropna().reset_index(drop=True); n=len(frame); c1=int(n*.6); c2=int(n*.8); val,test=frame.iloc[c1:c2],frame.iloc[c2:]
        best=min(WINDOWS,key=lambda w:mean_absolute_error(val.target,val[f'rm{w}'])); true=test.current.reset_index(drop=True); targ=test.target.reset_index(drop=True); scenarios={}
        for miss in [.1,.3]:
            imps=[]
            for seed in range(20):
                rr=np.random.default_rng(seed); corr=true.copy(); mask=rr.random(len(corr))<miss; mask[0]=False; corr[mask]=np.nan; corr=corr.ffill(); mp=mean_absolute_error(targ,corr); mr=mean_absolute_error(targ,corr.rolling(best,min_periods=1).mean()); imps.append(100*(mp-mr)/mp)
            scenarios[f'random_missing_{int(miss*100)}pct']={'mean_improvement_pct':float(np.mean(imps)),'p10_improvement_pct':float(np.quantile(imps,.1))}
        for block in [10,40,120]:
            imps=[]
            for seed in range(20):
                rr=np.random.default_rng(seed); corr=true.copy(); starts=rr.integers(1,max(2,len(corr)-block),size=10)
                for st in starts: corr.iloc[st:st+block]=np.nan
                corr=corr.ffill(); mp=mean_absolute_error(targ,corr); mr=mean_absolute_error(targ,corr.rolling(best,min_periods=1).mean()); imps.append(100*(mp-mr)/mp)
            scenarios[f'block_missing_{block}_samples']={'mean_improvement_pct':float(np.mean(imps)),'p10_improvement_pct':float(np.quantile(imps,.1))}
        for noise in [.005,.02]:
            imps=[]; sigma=float(true.std()*noise)
            for seed in range(20):
                rr=np.random.default_rng(seed); corr=true+rr.normal(0,sigma,len(true)); mp=mean_absolute_error(targ,corr); mr=mean_absolute_error(targ,corr.rolling(best,min_periods=1).mean()); imps.append(100*(mp-mr)/mp)
            scenarios[f'gaussian_noise_{noise*100:.1f}pct_std']={'mean_improvement_pct':float(np.mean(imps)),'p10_improvement_pct':float(np.quantile(imps,.1))}
        out[str(h)]={'horizon_minutes':h/2.0,'selected_window':best,'scenarios':scenarios}
    return out

def forge_drift(d: pd.DataFrame) -> dict:
    q=d[(d.pump_rate>1) & d.recovery_proxy.between(0,2)].dropna(subset=['recovery_proxy','sep_total','pump_rate','p16a','p16b','temp16b']).reset_index(drop=True); cols=['recovery_proxy','sep_total','pump_rate','p16a','p16b','temp16b']; n=len(q); blocks=[q.iloc[int(n*i/5):int(n*(i+1)/5)] for i in range(5)]; out={'block_rows':[len(b) for b in blocks],'variables':{}}
    for c in cols:
        base=blocks[0][c].values; iqr=np.quantile(base,.75)-np.quantile(base,.25); comps=[]
        for j,b in enumerate(blocks[1:],2):
            v=b[c].values; comps.append({'block':j,'ks':float(ks_2samp(base,v).statistic),'wasserstein_normalized_by_base_iqr':float(wasserstein_distance(base,v)/max(iqr,1e-9)),'median':float(np.median(v))})
        out['variables'][c]={'block1_median':float(np.median(base)),'comparisons':comps}
    return out

def load_1149_cycle1(path: Path) -> pd.DataFrame:
    d=pd.read_excel(path,sheet_name='Cycle 1',header=2)
    q=pd.DataFrame({'spp':pd.to_numeric(d.get('SPP (psi)'),errors='coerce'),'pump':pd.to_numeric(d.get('Pump 3 Rate (gpm)'),errors='coerce'),'casing':pd.to_numeric(d.get('Casing (psi)'),errors='coerce'),'temp':pd.to_numeric(d.get('TEMP IN (F)'),errors='coerce')})
    return q[(q.spp.between(0,12000)) & q.pump.between(0,200)].reset_index(drop=True)

def state_forecast_screen(q: pd.DataFrame) -> dict:
    f=pd.DataFrame(index=q.index)
    for lag in [0,1,3,6,12,30]:
        f[f'spp_l{lag}']=q.spp.shift(lag) if lag else q.spp; f[f'pump_l{lag}']=q.pump.shift(lag) if lag else q.pump
    f['spp_slope6']=(q.spp-q.spp.shift(6))/6; f['pump_slope6']=(q.pump-q.pump.shift(6))/6; f['pump_dir']=np.sign(q.pump-q.pump.shift(3)); f['casing']=q.casing; f['temp']=q.temp.ffill(); out={}
    for h in [6,18,36]:
        data=f.copy(); data['target']=q.spp.shift(-h); data=data.dropna(); n=len(data); c1=int(n*.6); c2=int(n*.8); tr,te=data.iloc[:c1],data.iloc[c2:]; X=[c for c in data.columns if c!='target']; model=make_pipeline(StandardScaler(),Ridge(alpha=10.0)); model.fit(tr[X],tr.target); pred=model.predict(te[X]); mp=mean_absolute_error(te.target,te['spp_l0']); mm=mean_absolute_error(te.target,pred); imp=100*(mp-mm)/mp; out[str(h)]={'horizon_seconds':h*10,'n_test':len(te),'persistence_mae':float(mp),'state_ridge_mae':float(mm),'improvement_pct':float(imp),'status':'PROMOTE_FOR_FURTHER_TEST' if imp>=5 else 'HOLD_OR_NEGATIVE'}
    return out

def read_ndbc(path: Path) -> pd.DataFrame:
    lines=path.read_text(errors='replace').splitlines(); header=lines[0].lstrip('#').split(); rows=[]
    for line in lines[2:]:
        parts=line.split()
        if len(parts)>=len(header): rows.append(parts[:len(header)])
    d=pd.DataFrame(rows,columns=header)
    for c in header: d[c]=pd.to_numeric(d[c].replace('MM',np.nan),errors='coerce')
    d['time']=pd.to_datetime(dict(year=d.YY,month=d.MM,day=d.DD,hour=d.hh,minute=d.mm),errors='coerce',utc=True); d=d.sort_values('time').reset_index(drop=True); d['proxy']=WAVE_KW_M*d.WVHT**2*d.APD
    for c in ['MWD','WDIR']:
        rad=np.deg2rad(d[c]); d[c+'_sin']=np.sin(rad); d[c+'_cos']=np.cos(rad)
    return d

def wave_feature_and_robustness(wave_dir: Path) -> dict:
    stations={}
    for p in sorted(wave_dir.glob('*.txt')):
        d=read_ndbc(p)
        if d.proxy.notna().sum()>=200: stations[p.stem]=d
    screen=[]; robustness={}
    for sid,d0 in stations.items():
        d=d0[d0.proxy.notna()].copy().reset_index(drop=True); step=float(d.time.diff().dt.total_seconds().div(60).median()); base_cols=['proxy','WVHT','APD','DPD','WSPD','GST','PRES','ATMP','WTMP','MWD_sin','MWD_cos','WDIR_sin','WDIR_cos']
        for c in base_cols:
            for lag in [0,1,3,6]: d[f'{c}_l{lag}']=d[c].shift(lag) if lag else d[c]
        for w in [3,6,12]: d[f'proxy_rm{w}']=d.proxy.rolling(w,min_periods=1).mean()
        robustness[sid]={}
        for hmin in [60,180,360]:
            hs=max(1,round(hmin/step)); q=d.copy(); q['target']=q.proxy.shift(-hs); feat=[c for c in q.columns if '_l' in c]+['proxy_rm3','proxy_rm6','proxy_rm12']; data=q[feat+['target']].dropna(subset=['target']); n=len(data); c1=int(n*.6); c2=int(n*.8); tr,val,te=data.iloc[:c1],data.iloc[c1:c2],data.iloc[c2:]
            if len(te)<100: continue
            best=min([3,6,12],key=lambda w:mean_absolute_error(val.target,val[f'proxy_rm{w}'])); model=HistGradientBoostingRegressor(max_iter=150,max_leaf_nodes=15,learning_rate=.05,l2_regularization=2,random_state=SEED); model.fit(tr[feat],tr.target); pred=model.predict(te[feat]); mp=mean_absolute_error(te.target,te['proxy_l0']); mr=mean_absolute_error(te.target,te[f'proxy_rm{best}']); mh=mean_absolute_error(te.target,pred); roll_imp=100*(mp-mr)/mp
            screen.append({'station':sid,'horizon_minutes':hmin,'n_test':len(te),'rolling_window':best,'rolling_improvement_pct':float(roll_imp),'rich_feature_hgb_improvement_pct':float(100*(mp-mh)/mp)})
            if roll_imp>0:
                true=te['proxy_l0'].reset_index(drop=True); targ=te.target.reset_index(drop=True); sc={}
                for miss in [.1,.3]:
                    vals=[]
                    for seed in range(30):
                        rr=np.random.default_rng(seed); corr=true.copy(); mask=rr.random(len(corr))<miss; mask[0]=False; corr[mask]=np.nan; corr=corr.ffill(); a=mean_absolute_error(targ,corr); b=mean_absolute_error(targ,corr.rolling(best,min_periods=1).mean()); vals.append(100*(a-b)/a)
                    sc[f'missing_{int(miss*100)}pct']={'mean_improvement_pct':float(np.mean(vals)),'p10_improvement_pct':float(np.quantile(vals,.1))}
                robustness[sid][str(hmin)]={'base_rolling_improvement_pct':float(roll_imp),'selected_window':best,'scenarios':sc}
    ser={}
    for sid,d in stations.items():
        if d.time.max()>=pd.Timestamp('2026-09-01',tz='UTC'): ser[sid]=d.set_index('time').proxy.resample('1h').median()
    panel=pd.DataFrame(ser).sort_index(); cross=[]
    if panel.shape[1]>=2:
        sids=list(panel.columns)
        for target in sids:
            for h in [1,3,6]:
                f=pd.DataFrame(index=panel.index)
                for sid in sids:
                    for lag in [0,1,3,6]: f[f'{sid}_l{lag}']=panel[sid].shift(lag)
                f['target']=panel[target].shift(-h); data=f.dropna(subset=[f'{target}_l0','target']); n=len(data); c1=int(n*.6); c2=int(n*.8); tr,te=data.iloc[:c1],data.iloc[c2:]
                if len(te)<100: continue
                X=[c for c in data.columns if c!='target']; m=HistGradientBoostingRegressor(max_iter=120,max_leaf_nodes=10,learning_rate=.05,l2_regularization=3,random_state=SEED); m.fit(tr[X],tr.target); pred=m.predict(te[X]); mp=mean_absolute_error(te.target,te[f'{target}_l0']); mm=mean_absolute_error(te.target,pred); cross.append({'target_station':target,'horizon_hours':h,'n_test':len(te),'cross_station_improvement_pct':float(100*(mp-mm)/mp)})
    return {'station_feature_screen':screen,'rolling_robustness':robustness,'cross_station_screen':cross}

def usgs_consensus_and_risk(table1: Path, table2: Path) -> dict:
    t1=pd.read_csv(table1); est=['Chalcedony_degC','Opal_degC','Giggenbach_degC','KMg_degC','Na_K_degC','NaK_13_Ca_degC','NaK_43_Ca_degC','Mg_corr_NaK_43_Ca_degC']; E=t1[est].apply(pd.to_numeric,errors='coerce'); E=E[E.notna().sum(axis=1)>=5].reset_index(drop=True); ref=E.median(axis=1,skipna=True).values
    def trimmed(row):
        v=np.sort(row[~np.isnan(row)]); v=v[1:-1] if len(v)>=5 else v; return float(np.mean(v)) if len(v) else np.nan
    drop={}
    for frac in [.2,.4,.6]:
        stats={'median':[],'mean':[],'trimmed':[]}; ranks={'median':[],'mean':[],'trimmed':[]}
        for seed in range(100):
            rr=np.random.default_rng(seed); A=E.to_numpy(float).copy()
            for i in range(A.shape[0]):
                obs=np.where(~np.isnan(A[i]))[0]; dropidx=obs[rr.random(len(obs))<frac]; dropidx=dropidx[:max(0,len(obs)-2)] if len(obs)-len(dropidx)<2 else dropidx; A[i,dropidx]=np.nan
            preds={'median':np.nanmedian(A,axis=1),'mean':np.nanmean(A,axis=1),'trimmed':np.array([trimmed(r) for r in A])}
            for name,p in preds.items(): stats[name].append(float(np.nanmean(np.abs(p-ref)))); ranks[name].append(float(spearmanr(p,ref,nan_policy='omit').statistic))
        drop[str(frac)]={name:{'mae_degC':float(np.mean(stats[name])),'mae_p90_degC':float(np.quantile(stats[name],.9)),'spearman':float(np.mean(ranks[name]))} for name in stats}
    t2=pd.read_csv(table2); cols=['Minimum_Reservoir_Temperature_degC','Maximum_Reservoir_Temperature_degC','Most_Likely_Reservoir_Temperature_degC','Mean_Reservoir_Temperature_degC','Mean_Accessible_Resource_Base_10to18_J','PlusMinus_of_Mean_Accessible_Resource_Base_10to18_J']
    for c in cols: t2[c]=pd.to_numeric(t2[c],errors='coerce')
    u=t2.dropna(subset=['Minimum_Reservoir_Temperature_degC','Maximum_Reservoir_Temperature_degC','Mean_Reservoir_Temperature_degC','Mean_Accessible_Resource_Base_10to18_J','PlusMinus_of_Mean_Accessible_Resource_Base_10to18_J']).copy(); u=u[u['Mean_Accessible_Resource_Base_10to18_J']>0].reset_index(drop=True)
    res=np.log1p(u.Mean_Accessible_Resource_Base_10to18_J.values); temp=u.Mean_Reservoir_Temperature_degC.values; zres=(res-res.mean())/res.std(); ztemp=(temp-temp.mean())/temp.std(); point=zres+ztemp; rel=(u.PlusMinus_of_Mean_Accessible_Resource_Base_10to18_J/u.Mean_Accessible_Resource_Base_10to18_J).values; trange=(u.Maximum_Reservoir_Temperature_degC-u.Minimum_Reservoir_Temperature_degC).values; zunc=(rel-rel.mean())/rel.std(); ztr=(trange-trange.mean())/trange.std(); n=len(u); k=max(1,int(.1*n)); rng=np.random.default_rng(123); mn=u.Minimum_Reservoir_Temperature_degC.values.astype(float); ml=u.Most_Likely_Reservoir_Temperature_degC.fillna(u.Mean_Reservoir_Temperature_degC).values.astype(float); mx=u.Maximum_Reservoir_Temperature_degC.values.astype(float); ml=np.minimum(np.maximum(ml,mn),mx); mu=u.Mean_Accessible_Resource_Base_10to18_J.values.astype(float); sd=u.PlusMinus_of_Mean_Accessible_Resource_Base_10to18_J.values.astype(float); eq=mx<=mn; sims=np.empty((500,n),dtype=np.float32)
    for s in range(500):
        st=np.empty(n); st[eq]=mn[eq]; idx=~eq; st[idx]=rng.triangular(mn[idx],ml[idx],mx[idx]); sr=np.maximum(1e-9,rng.normal(mu,sd)); sims[s]=(((np.log1p(sr)-res.mean())/res.std())+((st-temp.mean())/temp.std())).astype(np.float32)
    frontier=[]
    for lam in [0,.25,.5,.75,1.0]:
        score=point-lam*zunc-0.5*lam*ztr; sel=np.argsort(score)[-k:]; arr=sims[:,sel]; pm=arr.mean(axis=1); frontier.append({'penalty_lambda':lam,'selected_count':k,'portfolio_mean_score_avg':float(pm.mean()),'portfolio_mean_score_p10':float(np.quantile(pm,.1)),'mean_individual_p10':float(np.quantile(arr,.1,axis=0).mean()),'mean_individual_score_sd':float(arr.std(axis=0).mean())})
    return {'consensus_reference_note':'Full-data per-site median is an internal reconciliation reference, not ground truth.','sites_with_at_least_5_estimators':len(E),'estimator_dropout':drop,'resource_risk_frontier':frontier,'risk_frontier_note':'Penalty reduces dispersion but also reduces expected score; this is a risk-return tradeoff, not a universal superiority result.'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--forge1683-xlsx',type=Path,required=True); ap.add_argument('--forge1149-openhole',type=Path,required=True); ap.add_argument('--wave-dir',type=Path,required=True); ap.add_argument('--usgs-table1',type=Path,required=True); ap.add_argument('--usgs-table2',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    f=load_forge1683(args.forge1683_xlsx); c=load_1149_cycle1(args.forge1149_openhole)
    result={'schema_version':'1.0','claim_boundary':'Offline retrospective screening only. No live control, setpoint, safety limit, site recommendation, bankability, reserve estimate, or external validation is produced.','forge1683':{'rows':len(f),'walk_forward':forge_walkforward(f),'sensor_robustness':forge_sensor_robustness(f),'distribution_drift':forge_drift(f)},'forge1149_state_forecast':{'rows':len(c),'screen':state_forecast_screen(c)},'wave':wave_feature_and_robustness(args.wave_dir),'usgs':usgs_consensus_and_risk(args.usgs_table1,args.usgs_table2),'negative_results_retained':True}
    (args.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n'); manifest={}
    for p in [args.forge1683_xlsx,args.forge1149_openhole,args.usgs_table1,args.usgs_table2]: manifest[str(p)]=sha256_file(p)
    for p in sorted(args.wave_dir.glob('*.txt')): manifest[str(p)]=sha256_file(p)
    (args.out/'source_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps({'status':'ok','out':str(args.out/'summary.json')}))
if __name__=='__main__': main()
