import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {emptyWorkspace,validateWorkspace,workspaceStartupChoice,mergeScoutOpportunities,reviewWork,energyComparison,reviewEnergyChange,ENERGY_CONSTRAINT_UNITS,parsePriceCSV,paperBacktest,examplePrices,draftGrant,careReview} from '../dashboard/cohort/core.js';

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
  const context=vm.createContext({document:{querySelector:node},structuredClone,TextDecoder,emptyWorkspace,validateWorkspace,workspaceStartupChoice,
    examplePrices,energyComparison,reviewEnergyChange,mergeScoutOpportunities,ENERGY_CONSTRAINT_UNITS,crypto:{randomUUID:()=>`test-${++timerId}`},STAGES:[],STAGE_NAMES:{},fetch:fetcher,console,
    setTimeout(fn){const id=++timerId;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);},
    localStorage:{setItem(k,v){storage.set(k,v);}},initial:structuredClone(local)});
  const source=fs.readFileSync(new URL('../dashboard/cohort/studio.js',import.meta.url),'utf8').replace(/^import[^\n]*\n/,'').replace(/\binit\(\);\s*$/,'');
  vm.runInContext(source,context);
  vm.runInContext("member={id:'excalis',name:'Excalis'};state=initial;runtime=true;render=()=>{};modal=(title,body,onSubmit)=>{globalThis.dialog={title,body,onSubmit};};download=(name,text)=>{globalThis.downloads.push({name,text});};globalThis.downloads=[];globalThis.inspect=()=>({state:structuredClone(state),revision:backupRevision,paused:backupPaused,pending:backupPending,busy:backupBusy});globalThis.addRecord=id=>{state.scout.push({id,title:id});save();};",context);
  return {context,node,storage,async flush(){const callbacks=[...timers.values()];timers.clear();for(const callback of callbacks)await callback();}};
}
const response=(value,status=200)=>({ok:status>=200&&status<300,status,json:async()=>structuredClone(value)});
const statusResponse=()=>response({member:'excalis',ready:true,workspace_revision_check:true});

test('scout searches the owner project topic instead of silently using the industry',async()=>{
  const sent=[];
  const h=backupHarness(emptyWorkspace('excalis'),async(url,options)=>{
    sent.push(JSON.parse(options.body));
    return response({query:'wave energy',opportunities:[],source_receipt:{retrieved_utc:'2026-10-25T12:00:00Z'}});
  });
  vm.runInContext("member.industry='Manufacturing';",h.context);
  h.node('#scout-query').value='  wave energy  ';
  await vm.runInContext("action('scan-grants')",h.context);
  assert.equal(sent.length,1);
  assert.equal(sent[0].query,'wave energy');
});

test('scout never evicts saved owner records when a search reaches workspace capacity',async()=>{
  const initial=emptyWorkspace('excalis');
  initial.scout=Array.from({length:500},(_,i)=>({id:`saved-${i}`,title:`Owner record ${i}`,url:`https://example.test/${i}`,next_step:'Owner notes must survive'}));
  const incoming=Array.from({length:20},(_,i)=>({title:`Source listing ${i}`,url:`https://www.grants.gov/search-results-detail/${10000+i}`}));
  const h=backupHarness(initial,async()=>response({query:'wave energy',opportunities:incoming,source_receipt:{retrieved_utc:'2026-10-25T12:00:00Z'}}));
  vm.runInContext("member.industry='Manufacturing';",h.context);
  h.node('#scout-query').value='wave energy';
  await vm.runInContext("action('scan-grants')",h.context);
  assert.deepEqual(h.context.inspect().state.scout,initial.scout);
  assert.match(h.node('#toast').textContent,/20.*not imported|20.*capacity/i);
});

test('scout merges only available slots, preserves owner edits, and reports duplicates separately',()=>{
  const saved=Array.from({length:499},(_,i)=>({id:`saved-${i}`,title:`Owner ${i}`,url:`https://example.test/${i}`,next_step:'Keep this annotation'}));
  const before=structuredClone(saved);
  const result=mergeScoutOpportunities(saved,[{title:'Changed source title',url:saved[0].url},{title:'First new listing',url:'https://example.test/new'},{title:'Repeated listing',url:'https://example.test/new'},{title:'Second new listing',url:'https://example.test/overflow'}],{query:' wave energy ',retrievedAt:'2026-10-25T12:00:00Z',createId:()=> 'new-id'});
  assert.deepEqual(saved,before);
  assert.deepEqual(result.items.slice(0,499),before);
  assert.deepEqual({added:result.added,duplicates:result.duplicates,capacitySkipped:result.capacitySkipped},{added:1,duplicates:2,capacitySkipped:1});
  assert.equal(result.items[499].source_query,'wave energy');
  assert.equal(result.items[499].source_retrieved_utc,'2026-10-25T12:00:00Z');
});

test('scout rejects incomplete source results atomically and rejects unsafe links',()=>{
  const saved=[{id:'original',title:'Owner record',url:'https://example.test/old'}];
  for(const url of ['javascript:alert(1)','https://user:secret@example.test/','not a URL']){
    assert.throws(()=>mergeScoutOpportunities(saved,[{title:'New',url:'https://example.test/new'},{title:'Invalid',url}],{query:'wave',retrievedAt:'2026-10-25T12:00:00Z'}));
    assert.equal(saved.length,1);
  }
});

test('scout reports every unimported result at capacity without calling it saved',()=>{
  const saved=Array.from({length:500},(_,i)=>({id:`saved-${i}`,url:`https://example.test/${i}`}));
  const row={title:'Not saved',url:'https://example.test/overflow'};
  const result=mergeScoutOpportunities(saved,[row,row],{query:'wave',retrievedAt:'2026-10-25T12:00:00Z'});
  assert.equal(result.capacitySkipped,2);assert.equal(result.duplicates,0);assert.equal(result.added,0);
  assert.deepEqual(result.items,saved);
});

test('scout requires a nonempty explicit topic before requesting public data',async()=>{
  let calls=0;
  const h=backupHarness(emptyWorkspace('excalis'),async()=>{calls++;return response({});});
  h.node('#scout-query').value='   ';
  await vm.runInContext("action('scan-grants')",h.context);
  assert.equal(calls,0);assert.match(h.node('#toast').textContent,/Enter a project topic/);
});

test('latest scout download retains the complete returned set even when the workspace is full',async()=>{
  const initial=emptyWorkspace('excalis');
  initial.scout=Array.from({length:500},(_,i)=>({id:`owner-${i}`,title:`Saved ${i}`}));
  const result={query:'wave energy',returned_count:20,total_available:135,source_receipt:{retrieved_utc:'2026-10-25T12:00:00Z'},opportunities:Array.from({length:20},(_,i)=>({title:`Listing ${i}`,url:`https://www.grants.gov/search-results-detail/${10000+i}`}))};
  const scheduled={...result,query:'Manufacturing',opportunities:[]};
  const h=backupHarness(initial,async()=>response({schedules:{},errors:{},scout:scheduled,scout_manual:result,scout_scheduled:scheduled,paper:null}));
  h.context.document.querySelectorAll=()=>[];
  h.node('#runtime-activity').querySelectorAll=()=>[];
  await h.context.loadActivity();
  h.node('#export-scout-results').onclick();
  assert.equal(h.context.downloads.length,1);
  assert.equal(h.context.downloads[0].name,'excalis-grant-search-results.json');
  assert.deepEqual(JSON.parse(h.context.downloads[0].text),result);
  assert.deepEqual(h.context.inspect().state.scout,initial.scout);
});

test('scout leaves the workspace unchanged when the full backup would exceed its size limit',async()=>{
  const initial=emptyWorkspace('excalis');initial.measurements=[{notes:''}];
  initial.measurements[0].notes='x'.repeat(999999-JSON.stringify(initial).length);
  validateWorkspace(initial,'excalis');
  const h=backupHarness(initial,async()=>response({opportunities:[{title:'New grant',url:'https://example.test/new'}],source_receipt:{retrieved_utc:'2026-10-25T12:00:00Z'}}));
  h.node('#scout-query').value='wave';
  await vm.runInContext("action('scan-grants')",h.context);
  assert.equal(h.context.inspect().state.scout.length,0);
  assert.equal(h.context.inspect().state.measurements[0].notes.length,initial.measurements[0].notes.length);
  assert.match(h.node('#toast').textContent,/1 MB/);
});

test('Unicode expansion cannot change scout state before the local backup rejects its size',async()=>{
  const initial=emptyWorkspace('excalis');initial.measurements=[{notes:'😀'.repeat(90000)}];
  validateWorkspace(initial,'excalis'); // Legacy browser records remain readable.
  const h=backupHarness(initial,async()=>response({opportunities:[{title:'New',url:'https://example.test/new'}],source_receipt:{retrieved_utc:'2026-10-25T12:00:00Z'}}));
  h.node('#scout-query').value='wave';await vm.runInContext("action('scan-grants')",h.context);
  assert.deepEqual(h.context.inspect().state,initial);
  assert.match(h.node('#toast').textContent,/1 MB/);
});

test('workspace import rejects Unicode expansion and reserves the local request envelope before replacing records',async()=>{
  for(const notes of ['😀'.repeat(90000),'x'.repeat(999800)]){
    const incoming=emptyWorkspace('excalis');incoming.measurements=[{notes}];
    const initial=emptyWorkspace('excalis');initial.scout=[{id:'keep',title:'Keep owner record'}];
    const h=backupHarness(initial,async()=>{throw new Error('Unexpected network');});
    h.context.importWorkspace();const raw=JSON.stringify(incoming);
    await assert.rejects(h.context.dialog.onSubmit({get:()=>({size:Buffer.byteLength(raw),text:async()=>raw,arrayBuffer:async()=>Buffer.from(raw)})}),/1 MB/);
    assert.deepEqual(h.context.inspect().state,initial);
  }
});

test('malformed UTF-8 backup bytes cannot silently replace owner records with replacement characters',async()=>{
  const incoming=emptyWorkspace('excalis');incoming.measurements=[{notes:'X'}];
  const bytes=Buffer.from(JSON.stringify(incoming));bytes[bytes.indexOf(Buffer.from('"notes":"X"'))+9]=0xff;
  const initial=emptyWorkspace('excalis');initial.scout=[{id:'keep',title:'Keep owner record'}];
  const h=backupHarness(initial,async()=>{throw new Error('Unexpected network');});h.context.importWorkspace();
  await assert.rejects(h.context.dialog.onSubmit({get:()=>({size:bytes.length,text:async()=>new TextDecoder().decode(bytes),arrayBuffer:async()=>bytes})}),/UTF-8/);
  assert.deepEqual(h.context.inspect().state,initial);
});

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

// Entirely fictional declarations to test decision logic; these are not metrology.
const energyReviewTime='2026-09-12T10:00:00.000Z';
function energyFixture(){
  const source=role=>({source_id:'FICTIONAL-METER',evidence_ref:`FIXTURE-${role}`,sha256:'',started_at:'2026-09-12T08:00:00Z',ended_at:'2026-09-12T09:00:00Z',available_at:'2026-09-12T09:30:00Z',evidence_class:'metered_electricity'});
  return {measurement:{baseline_wh:100,candidate_wh:70,overhead_wh:5,baseline_accepted:10,candidate_accepted:10,baseline_attempted:12,candidate_attempted:15,equivalent:true,boundary_complete:true},
    service:{description:'Fictional batch',specification:'Test specification',conditions:'Test conditions',boundary:'Test complete batch',equivalence:'matched',evidence_ref:'FIXTURE-equivalence'},
    observations:{baseline:source('baseline'),candidate:source('candidate'),overhead:source('overhead')},overhead:{mode:'outside_meter',basis:'Fictional separately measured support',evidence_ref:'FIXTURE-overhead-accounting'},
    freshness_hours:2,action:{candidate_id:'TEST-CHANGE',allowed_ids:['TEST-CHANGE']},constraints_complete:true,
    constraints:[{id:'latency',unit:'ms',minimum:null,maximum:100,observed_min:80,observed_max:90,evidence_ref:'FIXTURE-latency'}],
    uncertainty:{bound_wh:2,minimum_net_wh:1,method:'Fictional aggregate error bound for logic testing',evidence_ref:'FIXTURE-uncertainty'},fallback:{baseline_id:'TEST-BASELINE',trigger:'Retain until separately authorized'}};
}
test('energy review preserves raw comparison and authorizes only an owner evidence review',()=>{
  const input=energyFixture(),before=structuredClone(input),r=reviewEnergyChange(input,energyReviewTime);
  assert.equal(r.decision,'CANDIDATE_FOR_REVIEW');assert.equal(r.actuation_authorized,false);
  assert.deepEqual(r.comparison,energyComparison(input.measurement));assert.deepEqual(input,before);
  assert.equal(r.fallback.action,'RETAIN_BASELINE');assert.equal(r.fallback.baseline_id,'TEST-BASELINE');
  assert.equal(r.source_verification,'REFERENCES_RECORDED_NOT_INDEPENDENTLY_VERIFIED');
  assert.ok(r.evidence_refs.includes('FIXTURE-overhead-accounting'));assert.ok(r.expected_effect.lower_bound_wh<23);
  assert.ok(r.expected_effect.lower_bound_wh>22.999999);assert.equal(r.expected_effect.declared_error_bound_wh,2);
});
test('non-wins, unresolved uncertainty, equal thresholds and binary residue cannot advance',()=>{
  for(const [baseline,candidate,overhead,bound,threshold,decision] of [
    [100,70,35,2,1,'RETAIN_BASELINE'],[100,95,5,2,1,'RETAIN_BASELINE'],
    [100,90,5,8,1,'EVIDENCE_INSUFFICIENT'],[100,90,5,2,3,'EVIDENCE_INSUFFICIENT'],
    [0.8,0.7,0.1,0,0,'EVIDENCE_INSUFFICIENT'],[1e12,1e12-0.0001,0,0,0,'EVIDENCE_INSUFFICIENT']]){
    const x=energyFixture();Object.assign(x.measurement,{baseline_wh:baseline,candidate_wh:candidate,overhead_wh:overhead});
    Object.assign(x.uncertainty,{bound_wh:bound,minimum_net_wh:threshold});const r=reviewEnergyChange(x,energyReviewTime);
    assert.equal(r.decision,decision,JSON.stringify([baseline,candidate,overhead,bound,threshold]));
    assert.equal(r.comparison.net_wh,energyComparison(x.measurement).net_wh);assert.equal(r.actuation_authorized,false);
  }
});
test('constraint intervals distinguish a known violation from uncertain compliance',()=>{
  for(const [low,high,decision] of [[105,110,'CONSTRAINT_FAILED'],[85,105,'EVIDENCE_INSUFFICIENT'],[100,100,'CANDIDATE_FOR_REVIEW'],[null,90,'EVIDENCE_INSUFFICIENT']]){
    const x=energyFixture();Object.assign(x.constraints[0],{observed_min:low,observed_max:high});
    const r=reviewEnergyChange(x,energyReviewTime);assert.equal(r.decision,decision);
    assert.equal(r.checks.find(c=>c.id==='constraint.latency').observed_interval.minimum,low);
  }
  const x=energyFixture();x.constraints[0].minimum=85;x.constraints[0].observed_max=80;
  assert.equal(reviewEnergyChange(x,energyReviewTime).decision,'CONSTRAINT_FAILED');
});
test('service, evidence, overhead and allowed-action gaps all abstain and retain their findings',()=>{
  const cases=[
    [x=>x.service.equivalence='mismatched','CONSTRAINT_FAILED'],
    [x=>x.measurement.candidate_accepted=9,'CONSTRAINT_FAILED'],
    [x=>x.measurement.equivalent=false,'EVIDENCE_INSUFFICIENT'],
    [x=>x.measurement.boundary_complete=false,'EVIDENCE_INSUFFICIENT'],
    [x=>x.service.specification='','EVIDENCE_INSUFFICIENT'],
    [x=>x.observations.candidate.evidence_class='modeled','EVIDENCE_INSUFFICIENT'],
    [x=>x.overhead.basis='','EVIDENCE_INSUFFICIENT'],
    [x=>x.action.allowed_ids=[],'EVIDENCE_INSUFFICIENT'],
    [x=>x.action.candidate_id='NOT-ALLOWED','CONSTRAINT_FAILED'],
    [x=>x.constraints=[],'EVIDENCE_INSUFFICIENT'],
    [x=>x.constraints_complete=false,'EVIDENCE_INSUFFICIENT'],
    [x=>x.uncertainty.bound_wh=null,'EVIDENCE_INSUFFICIENT'],
    [x=>x.uncertainty.method='','EVIDENCE_INSUFFICIENT'],
    [x=>x.fallback.baseline_id='','EVIDENCE_INSUFFICIENT']
  ];
  for(const [change,expected] of cases){const x=energyFixture();change(x);const r=reviewEnergyChange(x,energyReviewTime);assert.equal(r.decision,expected,change.toString());assert.equal(r.fallback.action,'RETAIN_BASELINE');assert.equal(r.actuation_authorized,false);}
  const x=energyFixture();x.observations.baseline.evidence_class='modeled';x.action.candidate_id='NOT-ALLOWED';x.constraints[0].observed_max=105;x.fallback.trigger='';
  const r=reviewEnergyChange(x,energyReviewTime);assert.equal(r.decision,'CONSTRAINT_FAILED');
  for(const id of ['source.baseline.class','action','constraint.latency','fallback'])assert.ok(r.checks.some(c=>c.id===id&&c.status!=='PASS'),id);
});
test('provenance and malformed values fail closed rather than becoming zero-valued evidence',()=>{
  const changes=[x=>x.observations.baseline.source_id='',x=>x.observations.candidate.evidence_ref='',
    x=>x.observations.baseline.started_at='2026-02-30T08:00:00Z',x=>x.observations.baseline.ended_at='2026-09-12T08:00:00Z',
    x=>x.observations.candidate.available_at='2026-09-12T10:00:01Z',x=>x.observations.candidate.available_at='2026-09-12T08:30:00Z',
    x=>x.observations.candidate.available_at='2026-09-12T09:30:00-00:00',x=>x.freshness_hours=0.5,
    x=>x.observations.baseline.sha256='not-a-hash',x=>x.constraints.push({...x.constraints[0]}),
    x=>x.constraints[0].unit='unknown-unit',x=>x.constraints[0].observed_min=95,
    x=>x.constraints[0].minimum=101,x=>x.action.allowed_ids.push('TEST-CHANGE'),
    x=>x.measurement.candidate_wh='',x=>x.measurement.baseline_wh=NaN,x=>x.measurement.overhead_wh=Infinity,
    x=>x.uncertainty.bound_wh=-1,x=>x.measurement.candidate_attempted=1,x=>x.measurement.baseline_accepted=0,
    x=>x.observations.candidate.evidence_class='POWER_VERIFIED',x=>x.service.equivalence='yes',
    x=>x.uncertainty.unrecognized_claim=true];
  for(const change of changes){const x=energyFixture();change(x);const r=reviewEnergyChange(x,energyReviewTime);assert.equal(r.decision,'DATA_INVALID',change.toString());assert.equal(r.actuation_authorized,false);}
  assert.equal(reviewEnergyChange(energyFixture(),'2026-02-30T10:00:00Z').decision,'DATA_INVALID');
  assert.equal(reviewEnergyChange(null,energyReviewTime).decision,'DATA_INVALID');
});
test('already-included and absent overhead need a referenced basis and cannot be counted again',()=>{
  for(const mode of ['included_in_candidate','none']){
    const x=energyFixture();x.overhead.mode=mode;x.observations.overhead=null;x.measurement.overhead_wh=0;
    assert.equal(reviewEnergyChange(x,energyReviewTime).decision,'CANDIDATE_FOR_REVIEW');
    x.overhead.basis='';assert.equal(reviewEnergyChange(x,energyReviewTime).decision,'EVIDENCE_INSUFFICIENT');
    x.overhead.basis='Fictional test basis';x.measurement.overhead_wh=5;
    assert.equal(reviewEnergyChange(x,energyReviewTime).decision,'DATA_INVALID');
  }
});
function energyFixtureForm(){
  const x=energyFixture(),f=new FormData();
  for(const [key,value] of Object.entries(x.measurement))f.append(key,typeof value==='boolean'?'on':String(value));
  f.append('source','FICTIONAL source, never a field result');
  for(const [key,value] of Object.entries(x.service))f.append(`service_${key}`,value);
  for(const [role,observation] of Object.entries(x.observations))for(const [key,value] of Object.entries(observation))f.append(`${role}_${key}`,value);
  for(const group of ['overhead','uncertainty','fallback'])for(const [key,value] of Object.entries(x[group]))f.append(`${group}_${key}`,String(value));
  f.append('action_candidate_id',x.action.candidate_id);f.append('action_allowed_ids',x.action.allowed_ids.join('\n'));
  f.append('freshness_hours',String(x.freshness_hours));f.append('constraints_complete','on');
  for(const row of x.constraints)for(const [key,value] of Object.entries(row))f.append(`constraint_${key}`,value===null?'':String(value));
  return f;
}
test('the actual form parser preserves source text, blank numeric fields and every repeated limit',()=>{
  const h=backupHarness(emptyWorkspace('excalis'),async()=>{throw new Error('Unexpected network');}),f=energyFixtureForm();
  const record=h.context.saveEnergyRecord(f,true,energyReviewTime);
  assert.equal(record.energy_review.decision,'CANDIDATE_FOR_REVIEW');assert.equal(record.review_inputs.observations.baseline.source_id,'FICTIONAL-METER');
  const encoded=JSON.parse(JSON.stringify(record));assert.deepEqual(encoded.raw_fields,[...f]);
  const w=JSON.parse(h.storage.get('luma-ec-studio-v1:excalis'));assert.equal(validateWorkspace(w,'excalis').measurements.length,1);
  f.set('candidate_wh','');f.append('constraint_id','second-limit');f.append('constraint_unit','W');
  for(const [key,value] of Object.entries({minimum:'',maximum:'50',observed_min:'',observed_max:'',evidence_ref:'Missing wattage observation'}))f.append(`constraint_${key}`,value);
  const incomplete=h.context.saveEnergyRecord(f,true,energyReviewTime);
  assert.equal(incomplete.inputs.candidate_wh,null);assert.equal(incomplete.energy_review.decision,'DATA_INVALID');
  assert.equal(incomplete.review_inputs.constraints.length,2);assert.equal(incomplete.raw_fields.filter(([key])=>key==='constraint_id').length,2);
  assert.equal(incomplete.review_inputs.constraints[1].observed_min,null);
  assert.throws(()=>h.context.saveEnergyRecord(f,false,energyReviewTime));
  for(const value of ['', ' ', '0x10', 'Infinity', 'NaN'])assert.equal(h.context.energyFormNumber(value),null);
  assert.equal(h.context.energyFormNumber('0'),0);assert.equal(h.context.energyFormNumber('1.5e2'),150);
});
test('review findings escape entered markup and legacy calculator records remain usable',()=>{
  const h=backupHarness(emptyWorkspace('excalis'),async()=>{throw new Error('Unexpected network');}),f=energyFixtureForm();
  f.set('constraint_id','<script>alert(1)</script>');const record=h.context.saveEnergyRecord(f,true,energyReviewTime);
  const html=h.context.energyResult(record);assert.ok(html.includes('&lt;script&gt;'));assert.ok(!html.includes('<script>'));
  const legacy=h.context.saveEnergyRecord(energyFixtureForm(),false,energyReviewTime);
  assert.equal(legacy.energy_review,undefined);assert.equal(legacy.result.net_wh,25);
  assert.match(h.context.energyResult(legacy),/Download this evidence record/);
});
test('the bound form distinguishes calculator and review submissions and reveals separate overhead inputs',()=>{
  const h=backupHarness(emptyWorkspace('excalis'),async()=>{throw new Error('Unexpected network');});
  const form=h.node('#energy-form');form.querySelector=h.node;form.querySelectorAll=()=>[];
  h.context.document.querySelectorAll=()=>[];
  h.context.FormData=function(target){return target.fields;};
  form.fields=energyFixtureForm();h.context.bindEnergyForm();
  const overhead=h.node('[name="overhead_mode"]');overhead.value='outside_meter';overhead.onchange();
  assert.equal(h.node('#overhead-observation').hidden,false);assert.equal(h.node('#overhead-observation').disabled,false);
  overhead.value='included_in_candidate';overhead.onchange();
  assert.equal(h.node('#overhead-observation').hidden,true);assert.equal(h.node('#overhead-observation').disabled,true);
  form.onsubmit({target:form,submitter:{value:'calculate'},preventDefault(){}});
  assert.equal(h.context.inspect().state.measurements[0].energy_review,undefined);
  form.fields.set('candidate_wh','');
  form.onsubmit({target:form,submitter:{value:'review'},preventDefault(){}});
  const saved=h.context.inspect().state.measurements;assert.equal(saved.length,2);
  assert.equal(saved[1].energy_review.decision,'DATA_INVALID');
  assert.match(h.node('#energy-result').innerHTML,/Correct the evidence record/);
});
