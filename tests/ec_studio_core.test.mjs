import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {emptyWorkspace,validateWorkspace,workspaceStartupChoice,reviewWork,energyComparison,parsePriceCSV,paperBacktest,examplePrices,draftGrant,careReview} from '../dashboard/cohort/core.js';

test('startup restores only an empty browser and preserves competing records for owner review',()=>{
  const local=emptyWorkspace('excalis'),saved=emptyWorkspace('excalis');
  saved.scout.push({id:'newer',title:'Newer saved record'});
  assert.equal(workspaceStartupChoice(local,null),'browser');
  assert.equal(workspaceStartupChoice(local,saved),'backup');
  local.scout.push({id:'older',title:'Older browser record'});
  assert.equal(workspaceStartupChoice(local,saved),'conflict');
  assert.equal(local.scout[0].id,'older');assert.equal(saved.scout[0].id,'newer');
  assert.equal(workspaceStartupChoice(saved,Object.fromEntries(Object.entries(saved).reverse())),'same');
  const reviewOnly=emptyWorkspace('excalis');reviewOnly.reviews.push({findings:[]});
  assert.equal(workspaceStartupChoice(reviewOnly,saved),'conflict');
  assert.throws(()=>workspaceStartupChoice(local,emptyWorkspace('hopeconnect-health')));
});

// Exercise the actual browser save/recovery handlers without starting a browser.
// Rendering is stubbed; these tests establish state transitions, not visual QA.
function backupHarness(local,fetcher){
  const nodes=new Map(),timers=new Map(),storage=new Map();let timerId=0;
  const node=selector=>{if(!nodes.has(selector))nodes.set(selector,{hidden:true,textContent:'',innerHTML:'',classList:{add(){},remove(){}},close(){}});return nodes.get(selector);};
  const context=vm.createContext({document:{querySelector:node},structuredClone,emptyWorkspace,validateWorkspace,workspaceStartupChoice,
    examplePrices,STAGES:[],STAGE_NAMES:{},fetch:fetcher,console,
    setTimeout(fn){const id=++timerId;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);},
    localStorage:{setItem(k,v){storage.set(k,v);}},initial:structuredClone(local)});
  const source=fs.readFileSync(new URL('../dashboard/cohort/studio.js',import.meta.url),'utf8').replace(/^import[^\n]*\n/,'').replace(/\binit\(\);\s*$/,'');
  vm.runInContext(source,context);
  vm.runInContext("member={id:'excalis',name:'Excalis'};state=initial;runtime=true;render=()=>{};modal=(title,body,onSubmit)=>{globalThis.dialog={title,body,onSubmit};};download=(name,text)=>{globalThis.downloads.push({name,text});};globalThis.downloads=[];globalThis.inspect=()=>({state:structuredClone(state),revision:backupRevision,paused:backupPaused,pending:backupPending,busy:backupBusy});globalThis.addRecord=id=>{state.scout.push({id,title:id});save();};",context);
  return {context,node,storage,async flush(){const callbacks=[...timers.values()];timers.clear();for(const callback of callbacks)await callback();}};
}
const response=(value,status=200)=>({ok:status>=200&&status<300,status,json:async()=>structuredClone(value)});
const statusResponse=()=>response({member:'excalis',ready:true,workspace_revision_check:true});

test('startup conflict performs no write and offers both versions before an owner chooses',async()=>{
  const local=emptyWorkspace('excalis'),remote=emptyWorkspace('excalis');
  local.scout=[{id:'older',title:'Older browser record'}];remote.scout=[{id:'newer',title:'Newer local backup'}];
  const writes=[];
  const h=backupHarness(local,async(url,options)=>{
    if(url.endsWith('/status'))return statusResponse();
    if(options.method==='POST'){writes.push(JSON.parse(options.body));return response({saved:true,revision:8});}
    return response({workspace:remote,revision:7});
  });
  await h.context.reconcileBackup();await h.flush();
  assert.equal(writes.length,0);assert.equal(h.context.inspect().paused,true);
  assert.equal(h.context.inspect().state.scout[0].id,'older');
  assert.match(h.node('#backup-notice-text').textContent,/Two saved versions/);
  h.context.reviewBackup();
  h.node('#download-browser-version').onclick();h.node('#download-local-version').onclick();
  assert.equal(JSON.parse(h.context.downloads[0].text).scout[0].id,'older');
  assert.equal(JSON.parse(h.context.downloads[1].text).scout[0].id,'newer');
  await h.context.dialog.onSubmit({get:()=> 'backup'});h.context.save();await h.flush();
  assert.equal(writes.length,1);assert.equal(writes[0].expected_revision,7);
  assert.equal(writes[0].workspace.scout[0].id,'newer');
});

test('edits made during an in-flight backup are sent afterward with the confirmed revision',async()=>{
  const writes=[];let finishFirst;
  const h=backupHarness(emptyWorkspace('excalis'),async(url,options)=>{
    if(url.endsWith('/status'))return statusResponse();
    if(options.method!=='POST')return response({workspace:null,revision:0});
    writes.push(JSON.parse(options.body));
    if(writes.length===1)return new Promise(resolve=>{finishFirst=()=>resolve(response({saved:true,revision:1}));});
    return response({saved:true,revision:2});
  });
  await h.context.reconcileBackup();h.context.addRecord('first');
  const saving=h.flush();await Promise.resolve();
  h.context.addRecord('second');assert.equal(writes.length,1);
  assert.equal(writes[0].workspace.scout.length,1);
  finishFirst();await saving;await h.flush();
  assert.equal(writes.length,2);assert.equal(writes[1].expected_revision,1);
  assert.deepEqual(writes[1].workspace.scout.map(x=>x.id),['first','second']);
  assert.equal(h.context.inspect().revision,2);
});

test('a rejected stale write pauses further backups and preserves unsent browser edits',async()=>{
  const remote=emptyWorkspace('excalis');remote.scout=[{id:'other-session',title:'Other session'}];
  let writes=0;
  const h=backupHarness(emptyWorkspace('excalis'),async(url,options)=>{
    if(url.endsWith('/status'))return statusResponse();
    if(options.method!=='POST')return response({workspace:null,revision:0});
    writes++;return response({detail:'Conflict',conflict:{workspace:remote,revision:1}},409);
  });
  await h.context.reconcileBackup();h.context.addRecord('unsent');await h.flush();
  h.context.addRecord('also-unsent');await h.flush();
  assert.equal(writes,1);assert.equal(h.context.inspect().paused,true);
  const kept=JSON.parse(h.storage.get('luma-ec-studio-v1:excalis'));
  assert.deepEqual(kept.scout.map(x=>x.id),['unsent','also-unsent']);
  assert.match(h.node('#backup-notice-text').textContent,/neither version is overwritten/);
});
test('member workspaces are isolated and malformed paper imports fail',()=>{
  const value=emptyWorkspace('excalis');assert.equal(validateWorkspace(value,'excalis').member,'excalis');
  assert.throws(()=>validateWorkspace(value,'hopeconnect-health'));
  assert.throws(()=>validateWorkspace({...value,paper:{mode:'paper'}},'excalis'));
});
test('workflow checks keep missing work and approval visible',()=>{
  const f=reviewWork([{id:'1',title:'Fictional job',stage:'in_progress',scope:'',acceptance:'',due:'',approved:false,file_hash:'abc',revision:''}]);
  assert.deepEqual(new Set(f.map(x=>x.kind)),new Set(['missing','approval','revision']));
});
test('energy accounting retains outside overhead and rejects false savings',()=>{
  const p={baseline_wh:100,candidate_wh:70,overhead_wh:35,baseline_accepted:10,candidate_accepted:10,baseline_attempted:12,candidate_attempted:15,equivalent:true,boundary_complete:true};
  const r=energyComparison(p);assert.equal(r.net_wh,-5);assert.equal(r.status,'OBSERVED_INCREASE');assert.equal(r.candidate_yield,10/15);
  assert.equal(energyComparison({...p,candidate_accepted:5}).net_wh,null);
  assert.equal(energyComparison({...p,equivalent:false}).comparison_allowed,false);
  assert.throws(()=>energyComparison({...p,candidate_accepted:0}));
  assert.throws(()=>energyComparison({...p,candidate_wh:NaN}));
});
test('prices require valid chronological unique dates and positive finite values',()=>{
  const csv=examplePrices();assert.equal(parsePriceCSV(csv).length,100);
  assert.throws(()=>parsePriceCSV(csv.replace('2025-01-02','2025-01-01')));
  assert.throws(()=>parsePriceCSV(csv.replace('2025-01-02','2025-02-30')));
  assert.throws(()=>parsePriceCSV(csv.replace('99.00','NaN')));
});
test('SMA fills use prior data, costs reduce equity, and no real order is authorized',()=>{
  const rows=parsePriceCSV(examplePrices());const r=paperBacktest(rows);
  assert.equal(r.live_authorized,false);assert.equal(r.mode,'paper');assert.ok(r.fills.length>0);assert.ok(r.fees>0);
  const prefix=rows.slice(0,60),truncated=paperBacktest(prefix);
  assert.deepEqual(r.fills.filter(f=>f.date<=prefix.at(-1).date),truncated.fills);
  const zero=paperBacktest(rows,{fee_bps:0,slippage_bps:0});assert.ok(r.equity<zero.equity);
  assert.ok(Math.abs(r.equity-(r.cash+r.position*rows.at(-1).close))<1e-6);
});
test('grant drafts retain unknown funding and applicant facts',()=>{
  const draft=draftGrant({name:'Example member',strength:'Public description.'},{project:'Owner supplied idea'});
  assert.match(draft,/OWNER TO COMPLETE: requested amount/);assert.match(draft,/OWNER TO COMPLETE: organization type/);
  assert.match(draft,/No application was submitted/);assert.doesNotMatch(draft,/\$0/);
});
test('nonclinical coordination catches an unconfirmed closed handoff',()=>{
  const result=careReview([{id:'FAKE-1',stage:'confirmed',owner:'coordinator',confirmed_at:''}]);assert.equal(result.length,1);assert.match(result[0].message,/confirmation timestamp/);
});
