import test from 'node:test';
import assert from 'node:assert/strict';
import {emptyWorkspace,validateWorkspace,reviewWork,energyComparison,parsePriceCSV,paperBacktest,examplePrices,draftGrant,careReview} from '../dashboard/cohort/core.js';
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
