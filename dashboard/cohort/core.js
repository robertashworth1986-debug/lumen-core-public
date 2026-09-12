/* Pure, offline member-workspace operations. No network, credentials or orders. */
export const SCHEMA = 'lumencore.ec_strength_studio.workspace.v1';
export const STAGES = ['inbox', 'review', 'in_progress', 'complete'];
export const STAGE_NAMES = {inbox:'Inbox', review:'Ready for review', in_progress:'In progress', complete:'Complete'};
export const MAX_ITEMS = 500;
export function emptyWorkspace(member) {
  return {schema:SCHEMA, member, items:[], measurements:[], grants:[], scout:[], care:[], reviews:[], paper:null};
}
export function validText(value, max=2000) { return typeof value === 'string' && value.length <= max; }
export function validateWorkspace(value, member) {
  if (!value || value.schema !== SCHEMA || value.member !== member) throw new Error('This file belongs to a different member or workspace version.');
  const expected=['schema','member','items','measurements','grants','scout','care','reviews','paper'];
  if(Object.keys(value).some(k=>!expected.includes(k))||Object.keys(value).length!==expected.length)throw new Error('Unexpected workspace fields.');
  for (const k of ['items','measurements','grants','scout','care','reviews']) {
    if (!Array.isArray(value[k]) || value[k].length > MAX_ITEMS) throw new Error(`Invalid or oversized ${k} collection.`);
  }
  const ids = new Set();
  for (const item of value.items) {
    if (!item || !validText(item.id,100) || ids.has(item.id) || !validText(item.title,180) || !item.title.trim() || !STAGES.includes(item.stage) || !validText(item.scope,3000) || !validText(item.acceptance,2000) || !validText(item.revision,100)) throw new Error('A work item is invalid or duplicated.');
    if(typeof item.approved!=='boolean'||(['in_progress','complete'].includes(item.stage)&&!item.approved))throw new Error('A progressed work item needs recorded owner acceptance.');
    ids.add(item.id);
  }
  for(const collection of ['measurements','grants','scout','care','reviews'])for(const row of value[collection])if(!row||typeof row!=='object'||Array.isArray(row))throw new Error(`Invalid ${collection} record.`);
  for(const g of value.grants)if(!validText(g.id,100)||!validText(g.title,600)||!validText(g.markdown,30000))throw new Error('Invalid grant draft.');
  for(const r of value.reviews)if(!Array.isArray(r.findings)||r.findings.length>2000)throw new Error('Invalid workflow review.');
  if(value.paper!==null){const p=value.paper;if(!p||p.mode!=='paper'||p.live_authorized!==false||!Array.isArray(p.fills)||p.fills.length>3000||!Array.isArray(p.curve)||p.curve.length<22||p.curve.length>3000)throw new Error('Invalid paper simulation.');for(const key of ['cash','equity','position','fees','pnl','drawdown'])if(typeof p[key]!=='number'||!Number.isFinite(p[key]))throw new Error('Invalid paper values.');for(const f of p.fills)if(!f||!['buy','sell'].includes(f.side)||!validText(f.date,30)||['quantity','price','fee'].some(k=>typeof f[k]!=='number'||!Number.isFinite(f[k])||f[k]<0))throw new Error('Invalid paper fill.');for(const c of p.curve)if(!c||!Number.isFinite(c.equity))throw new Error('Invalid equity curve.');}
  if (JSON.stringify(value).length > 1_000_000) throw new Error('Workspace is larger than the 1 MB import limit.');
  return structuredClone(value);
}
export function reviewWork(items) {
  const findings=[];
  for (const i of items) {
    if (i.stage === 'complete') continue;
    const missing = ['scope','acceptance','due'].filter(k=>!String(i[k]||'').trim());
    if (missing.length) findings.push({item:i.id,title:i.title,kind:'missing',message:`Add ${missing.join(', ')} before the handoff.`});
    if (i.stage === 'in_progress' && !i.approved) findings.push({item:i.id,title:i.title,kind:'approval',message:'Owner acceptance is not recorded. Review the brief before continuing.'});
    if (i.file_hash && !i.revision) findings.push({item:i.id,title:i.title,kind:'revision',message:'A file hash is recorded, but its approved revision is missing.'});
    if (i.due && /^\d{4}-\d{2}-\d{2}$/.test(i.due) && i.due < new Date().toISOString().slice(0,10)) findings.push({item:i.id,title:i.title,kind:'overdue',message:'The planned date has passed; confirm the next step with the owner.'});
  }
  return findings;
}
export function energyComparison(input) {
  const nums=['baseline_wh','candidate_wh','overhead_wh','baseline_accepted','candidate_accepted','baseline_attempted','candidate_attempted'];
  for(const key of nums) if(typeof input[key] !== 'number'||!Number.isFinite(input[key])||input[key]<0||input[key]>1e12) throw new Error(`Enter a finite, nonnegative ${key.replaceAll('_',' ')}.`);
  for(const key of ['baseline_accepted','candidate_accepted','baseline_attempted','candidate_attempted']) if(!Number.isInteger(input[key])) throw new Error('Part counts must be whole numbers.');
  if(input.baseline_accepted<1||input.candidate_accepted<1) throw new Error('Both batches need at least one accepted part. Zero output cannot establish an energy improvement.');
  if(input.baseline_attempted<input.baseline_accepted||input.candidate_attempted<input.candidate_accepted) throw new Error('Attempted parts must include every accepted and rejected part.');
  const totalCandidate=input.candidate_wh+input.overhead_wh;
  const baseUnit=input.baseline_wh/input.baseline_accepted;
  const candidateUnit=totalCandidate/input.candidate_accepted;
  const equivalent=input.equivalent===true && input.boundary_complete===true && input.baseline_accepted===input.candidate_accepted;
  return {baseline_wh_per_accepted:baseUnit,candidate_wh_per_accepted:candidateUnit,
    baseline_total_wh:input.baseline_wh,candidate_total_wh:totalCandidate,
    baseline_yield:input.baseline_accepted/input.baseline_attempted,candidate_yield:input.candidate_accepted/input.candidate_attempted,
    comparison_allowed:equivalent,net_wh:equivalent?input.baseline_wh-totalCandidate:null,
    percent:equivalent&&input.baseline_wh>0?100*(input.baseline_wh-totalCandidate)/input.baseline_wh:null,
    status:!equivalent?'NOT_COMPARABLE':totalCandidate<input.baseline_wh?'OBSERVED_REDUCTION_UNVALIDATED':totalCandidate>input.baseline_wh?'OBSERVED_INCREASE':'NO_CHANGE'};
}
export function parsePriceCSV(text) {
  if(typeof text!=='string'||text.length>500000) throw new Error('CSV must be under 500 KB.');
  const lines=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/);
  if(lines[0].toLowerCase().replaceAll(' ','')!=='date,open,close') throw new Error('Use the header date,open,close and ISO dates in chronological order.');
  const rows=lines.slice(1).filter(x=>x.trim()).map((line,i)=>{
    const p=line.split(',').map(x=>x.trim());
    const date=p[0];const open=Number(p[1]),close=Number(p[2]);
    if(p.length!==3||!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(Date.parse(date+'T00:00:00Z'))||new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date||!p[1]||!p[2]||!Number.isFinite(open)||!Number.isFinite(close)||open<=0||close<=0||open>1e9||close>1e9) throw new Error(`Invalid price row ${i+2}.`);
    return {date,open,close};
  });
  if(rows.length<22||rows.length>3000) throw new Error('Use 22 to 3,000 daily rows.');
  for(let i=1;i<rows.length;i++)if(rows[i].date<=rows[i-1].date) throw new Error('Dates must be unique and strictly increasing.');
  return rows;
}
export function paperBacktest(rows,{cash=10000,fee_bps=10,slippage_bps=5,allocation=.25}={}) {
  for(const n of [cash,fee_bps,slippage_bps,allocation])if(typeof n!=='number'||!Number.isFinite(n))throw new Error('Invalid simulation settings.');
  if(cash<1||cash>1e9||fee_bps<0||fee_bps>1000||slippage_bps<0||slippage_bps>1000||allocation<=0||allocation>1)throw new Error('Simulation settings are outside supported bounds.');
  if(!Array.isArray(rows)||rows.length<22||rows.length>3000)throw new Error('Invalid daily price history.');
  let balance=cash,qty=0,fees=0,peak=cash,drawdown=0;const fills=[],curve=[];
  const feeRate=fee_bps/10000,slip=slippage_bps/10000;
  // Decisions use only closes through yesterday; fills use today's open.
  for(let i=0;i<rows.length;i++){
    if(i>=20){
      const history=rows.slice(i-20,i);const slow=history.reduce((s,x)=>s+x.close,0)/20;
      const fast=history.slice(-5).reduce((s,x)=>s+x.close,0)/5;
      if(fast>slow&&qty===0){
        const price=rows[i].open*(1+slip);const spend=balance*allocation;
        const quantity=spend/(price*(1+feeRate));const fee=quantity*price*feeRate;
        balance-=quantity*price+fee;qty=quantity;fees+=fee;
        fills.push({date:rows[i].date,side:'buy',quantity,price,fee});
      }else if(fast<=slow&&qty>0){
        const price=rows[i].open*(1-slip);const fee=qty*price*feeRate;
        balance+=qty*price-fee;fees+=fee;fills.push({date:rows[i].date,side:'sell',quantity:qty,price,fee});qty=0;
      }
    }
    const equity=balance+qty*rows[i].close;peak=Math.max(peak,equity);drawdown=Math.max(drawdown,(peak-equity)/peak);
    curve.push({date:rows[i].date,equity});
  }
  const equity=curve.at(-1).equity;
  return {mode:'paper',strategy:'SMA 5/20, previous close signal / next open fill',initial_cash:cash,cash:balance,equity,position:qty,fees,pnl:equity-cash,drawdown,curve,fills,live_authorized:false};
}
export function examplePrices(){return 'date,open,close\n'+Array.from({length:100},(_,i)=>{const d=new Date(Date.UTC(2025,0,1+i)).toISOString().slice(0,10);const p=100+Math.sin(i/7)*8+i*.07;return `${d},${(p-Math.cos(i/4)).toFixed(2)},${p.toFixed(2)}`;}).join('\n');}
export function draftGrant(member, facts) {
  const need=(key)=>String(facts[key]||'').trim()||`[OWNER TO COMPLETE: ${key.replaceAll('_',' ')}]`;
  return `# ${member.name} — grant working draft\n\nStatus: DRAFT. Owner review and verified eligibility required.\n\n## Opportunity\n${need('opportunity')}\nOfficial source: ${need('source')}\nDeadline: ${need('deadline')}\n\n## Applicant facts\nLegal organization: ${need('legal_name')}\nOrganization type: ${need('organization_type')}\nRequested funding: ${need('requested_amount')}\n\n## Public business context\n${member.strength}\nThis is public positioning and remains subject to the owner's correction.\n\n## Proposed work\n${need('project')}\n\n## People served and need\n${need('beneficiaries')}\n\n## Activities and milestones\n${need('milestones')}\n\n## Measurement\n${need('measurement')}\n\n## Budget and evidence\n${need('budget')}\nSupporting evidence: ${need('evidence')}\n\n## Required owner checks\n- Read the official notice and every eligibility criterion.\n- Confirm applicant identity, registrations, costs, match and timing.\n- Attach only authorized evidence; preserve unknowns.\n- The authorized applicant reviews certifications and submits through the official portal.\n\nPrepared with LumenCore EC Strength Studio. No application was submitted.\n`;
}
export function careReview(records){
  return records.flatMap(r=>{
    const notes=[];if(!r.owner)notes.push('Assign a coordination owner.');
    if(r.stage!=='confirmed'&&!r.next_step)notes.push('Record the next nonclinical coordination step.');
    if(r.stage==='confirmed'&&!r.confirmed_at)notes.push('Add a confirmation timestamp before closing.');
    return notes.map(message=>({id:r.id,message}));
  });
}
