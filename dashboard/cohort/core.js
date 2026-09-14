/* Pure, offline member-workspace operations. No network, credentials or orders. */
export const SCHEMA = 'lumencore.ec_strength_studio.workspace.v1';
export const STAGES = ['inbox', 'review', 'in_progress', 'complete'];
export const STAGE_NAMES = {inbox:'Inbox', review:'Ready for review', in_progress:'In progress', complete:'Complete'};
export const MAX_ITEMS = 500;
export function emptyWorkspace(member) {
  return {schema:SCHEMA, member, items:[], measurements:[], grants:[], scout:[], care:[], reviews:[], paper:null};
}
export function validText(value, max=2000) { return typeof value === 'string' && value.length <= max; }
export function workspaceStartupChoice(local, saved) {
  validateWorkspace(local, local.member);
  if (saved === null) return 'browser';
  validateWorkspace(saved, local.member);
  const ordered=value=>Array.isArray(value)?value.map(ordered):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,ordered(value[k])])):value;
  if (JSON.stringify(ordered(local)) === JSON.stringify(ordered(saved))) return 'same';
  if (['items','measurements','grants','scout','care','reviews'].every(k=>local[k].length===0)&&local.paper===null) return 'backup';
  return 'conflict';
}
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
export const ENERGY_REVIEW_SCHEMA = 'lumencore.ec_strength_studio.energy_review.v1';
export const ENERGY_CONSTRAINT_UNITS = ['ms','s','min','W','Wh','kWh','degC','%','count','mm','Pa','dB'];
// Checks owner-entered historical evidence declarations. Never authorizes an action.
// No unit conversion, source retrieval, independent metrology or statistical fitting.
export function reviewEnergyChange(input, reviewedAt) {
  const checks=[],refs=new Set();
  const check=(id,status,message,details={})=>checks.push({id,status,message,...details});
  const text=(value,max=3000)=>typeof value==='string'&&value.trim().length>0&&value.length<=max;
  const finite=value=>typeof value==='number'&&Number.isFinite(value)&&Math.abs(value)<=1e12;
  const object=(value,id,keys)=>{
    if(!value||typeof value!=='object'||Array.isArray(value)){check(id,'DATA_INVALID',`${id}: a structured record is missing.`);return {};}
    if(Object.keys(value).some(k=>!keys.includes(k)))check(id,'DATA_INVALID',`${id}: unexpected fields need correction.`);
    return value;
  };
  const reference=value=>{if(text(value,600))refs.add(value.trim());};
  const stamp=value=>{
    if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value))return null;
    const ms=Date.parse(value);if(!Number.isFinite(ms))return null;
    return new Date(ms).toISOString()===(value.length===20?value.slice(0,-1)+'.000Z':value)?ms:null;
  };
  input=object(input,'input',['measurement','service','observations','overhead','action','constraints','constraints_complete','uncertainty','fallback','freshness_hours']);
  let comparison=null;
  try{comparison=energyComparison(input.measurement);}catch(error){check('measurement','DATA_INVALID',error.message);}
  const now=stamp(reviewedAt);
  if(now===null)check('review_time','DATA_INVALID','Record a valid review timestamp in UTC.');
  if(!finite(input.freshness_hours)||input.freshness_hours<=0)check('freshness_policy','DATA_INVALID','Declare a positive maximum measurement age in hours.');
  const service=object(input.service,'service',['description','specification','conditions','boundary','equivalence','evidence_ref']);
  for(const key of ['description','specification','conditions','boundary','evidence_ref'])if(!text(service[key],key==='evidence_ref'?600:3000))check(`service.${key}`,'EVIDENCE_INSUFFICIENT',`Describe the service ${key.replaceAll('_',' ')} before advancing.`);
  reference(service.evidence_ref);
  if(!['matched','mismatched','unknown'].includes(service.equivalence))check('service.equivalence','DATA_INVALID','Select matched, mismatched or unknown service equivalence.');
  else if(service.equivalence==='mismatched'||(comparison&&input.measurement.baseline_accepted!==input.measurement.candidate_accepted))check('service.equivalence','CONSTRAINT_FAILED','The declared service or accepted batch output differs. Retain the baseline.');
  else if(service.equivalence!=='matched'||input.measurement?.equivalent!==true)check('service.equivalence','EVIDENCE_INSUFFICIENT','Equivalent quality, conditions and useful output have not been declared.');
  else check('service.equivalence','PASS','Equivalent service is declared; the supporting reference still needs owner review.');
  if(input.measurement?.boundary_complete!==true)check('boundary','EVIDENCE_INSUFFICIENT','Full energy accounting, including failed work and rework, is not declared complete.');
  else check('boundary','PASS','Full energy accounting is declared complete; source completeness is not independently verified.');
  const observations=object(input.observations,'observations',['baseline','candidate','overhead']);
  const observation=(role)=>{
    const o=object(observations[role],`source.${role}`,['source_id','evidence_ref','sha256','started_at','ended_at','available_at','evidence_class']);
    let invalid=false;
    for(const key of ['source_id','evidence_ref'])if(!text(o[key],600)){check(`source.${role}.${key}`,'DATA_INVALID',`Add the ${role} ${key.replaceAll('_',' ')}.`);invalid=true;}
    reference(o.evidence_ref);
    if(o.sha256!==undefined&&o.sha256!==''&&(typeof o.sha256!=='string'||!/^[a-f0-9]{64}$/i.test(o.sha256))){check(`source.${role}.sha256`,'DATA_INVALID',`The ${role} artifact fingerprint must be 64 hexadecimal characters.`);invalid=true;}
    const start=stamp(o.started_at),end=stamp(o.ended_at),available=stamp(o.available_at);
    if(start===null||end===null||available===null||start>=end||end>available||(now!==null&&available>now)){
      check(`source.${role}.time`,'DATA_INVALID',`The ${role} timestamps must be valid UTC: start < end <= available <= review time.`);invalid=true;
    }else if(now!==null&&finite(input.freshness_hours)&&input.freshness_hours>0&&now-end>input.freshness_hours*3600000){
      check(`source.${role}.time`,'DATA_INVALID',`The ${role} measurement exceeds the declared maximum age.`);invalid=true;
    }
    if(!['metered_electricity','modeled','unknown'].includes(o.evidence_class)){check(`source.${role}.class`,'DATA_INVALID',`Select the ${role} evidence class.`);invalid=true;}
    else if(o.evidence_class!=='metered_electricity')check(`source.${role}.class`,'EVIDENCE_INSUFFICIENT',`The ${role} electricity effect has not been declared metered.`);
    if(!invalid)check(`source.${role}`,'PASS',`${role}: references and timing are recorded; the artifact has not been fetched or verified.`);
  };
  observation('baseline');observation('candidate');
  const overhead=object(input.overhead,'overhead',['mode','basis','evidence_ref']);
  reference(overhead.evidence_ref);
  if(!['outside_meter','included_in_candidate','none'].includes(overhead.mode))check('overhead.mode','DATA_INVALID','Select how additional overhead was accounted for.');
  if(!text(overhead.basis)||!text(overhead.evidence_ref,600))check('overhead.basis','EVIDENCE_INSUFFICIENT','Explain and reference overhead accounting, including a zero or already-included amount.');
  if(overhead.mode==='outside_meter')observation('overhead');
  else if(['included_in_candidate','none'].includes(overhead.mode)){
    if(input.measurement?.overhead_wh!==0)check('overhead.amount','DATA_INVALID','Already-included or absent overhead must have zero additional Wh; do not count it twice.');
    else check('overhead.amount','PASS','Zero additional overhead is declared; its accounting basis remains for owner review.');
    if(observations.overhead!==null&&observations.overhead!==undefined)check('overhead.source','DATA_INVALID','A separate overhead observation conflicts with the selected accounting mode.');
  }
  const action=object(input.action,'action',['candidate_id','allowed_ids']);
  if(!text(action.candidate_id,600))check('action','EVIDENCE_INSUFFICIENT','Identify the candidate change before reviewing it.');
  if(!Array.isArray(action.allowed_ids)||action.allowed_ids.length>20||action.allowed_ids.some(id=>!text(id,600))||new Set(action.allowed_ids.map(id=>typeof id==='string'?id.trim():id)).size!==action.allowed_ids.length)check('action.allowed_ids','DATA_INVALID','Use at most 20 distinct, nonempty allowed action IDs.');
  else if(!action.allowed_ids.length)check('action.allowed_ids','EVIDENCE_INSUFFICIENT','List the changes the owner has allowed for evaluation.');
  else if(text(action.candidate_id,600)){
    if(!action.allowed_ids.includes(action.candidate_id))check('action','CONSTRAINT_FAILED','The candidate action is outside the declared allowed set.');
    else check('action','PASS','The action ID is allowed for evaluation only. Execution is not authorized.');
  }
  if(input.constraints_complete!==true)check('constraints.complete','EVIDENCE_INSUFFICIENT','Confirm that all required hard limits and candidate-window observations are listed.');
  const constraints=Array.isArray(input.constraints)?input.constraints:[];
  if(!Array.isArray(input.constraints)||constraints.length>12)check('constraints','DATA_INVALID','Use an array of at most 12 hard constraints.');
  if(!constraints.length)check('constraints','EVIDENCE_INSUFFICIENT','At least one explicit hard operating limit is needed.');
  const ids=new Set();
  for(const [i,row] of constraints.slice(0,12).entries()){
    const c=object(row,`constraint.${i+1}`,['id','unit','minimum','maximum','observed_min','observed_max','evidence_ref']);
    const id=`constraint.${text(c.id,600)?c.id:i+1}`;
    reference(c.evidence_ref);
    if(!text(c.id,600)||ids.has(c.id.trim())){check(id,'DATA_INVALID','Constraint IDs must be nonempty and unique.');continue;}ids.add(c.id.trim());
    if(!ENERGY_CONSTRAINT_UNITS.includes(c.unit)||['minimum','maximum','observed_min','observed_max'].some(k=>c[k]!==null&&!finite(c[k]))){check(id,'DATA_INVALID','Use a supported unit and finite values, or null for an unknown or unused bound.');continue;}
    if((c.minimum!==null&&c.maximum!==null&&c.minimum>c.maximum)||(c.observed_min!==null&&c.observed_max!==null&&c.observed_min>c.observed_max)){check(id,'DATA_INVALID','Lower bounds cannot exceed upper bounds.');continue;}
    const detail={unit:c.unit,limits:{minimum:c.minimum,maximum:c.maximum},observed_interval:{minimum:c.observed_min,maximum:c.observed_max},evidence_ref:c.evidence_ref};
    if((c.minimum===null&&c.maximum===null)||c.observed_min===null||c.observed_max===null||!text(c.evidence_ref,600)){check(id,'EVIDENCE_INSUFFICIENT','A hard limit, conservative observed interval and evidence reference are required.',detail);continue;}
    if((c.minimum!==null&&c.observed_max<c.minimum)||(c.maximum!==null&&c.observed_min>c.maximum))check(id,'CONSTRAINT_FAILED','The entire declared observed interval lies outside a hard limit.',detail);
    else if((c.minimum!==null&&c.observed_min<c.minimum)||(c.maximum!==null&&c.observed_max>c.maximum))check(id,'EVIDENCE_INSUFFICIENT','The declared interval crosses a hard limit; compliance is unresolved.',detail);
    else check(id,'PASS','The declared observed interval is within the stated limits.',detail);
  }
  const uncertainty=object(input.uncertainty,'uncertainty',['bound_wh','minimum_net_wh','method','evidence_ref']);
  reference(uncertainty.evidence_ref);
  for(const k of ['bound_wh','minimum_net_wh']){
    if(uncertainty[k]===null)check(`uncertainty.${k}`,'EVIDENCE_INSUFFICIENT',`Declare ${k.replaceAll('_',' ')} in Wh.`);
    else if(!finite(uncertainty[k])||uncertainty[k]<0)check(`uncertainty.${k}`,'DATA_INVALID',`${k} must be finite and nonnegative.`);
  }
  if(!text(uncertainty.method)||!text(uncertainty.evidence_ref,600))check('uncertainty.basis','EVIDENCE_INSUFFICIENT','Document the aggregate uncertainty method and reference; meter accuracy alone does not cover the whole comparison.');
  const fallback=object(input.fallback,'fallback',['baseline_id','trigger']);
  if(!text(fallback.baseline_id,600)||!text(fallback.trigger))check('fallback','EVIDENCE_INSUFFICIENT','Identify the accepted baseline and the conditions that keep it in place.');
  let effect=null;
  if(comparison?.net_wh!==null&&comparison&&finite(uncertainty.bound_wh)&&uncertainty.bound_wh>=0&&finite(uncertainty.minimum_net_wh)&&uncertainty.minimum_net_wh>=0){
    // Outward allowance for binary input representation and the bounded arithmetic
    // above. Keep it separate from the owner's metrology/process error bound.
    const roundoff=Math.max(Number.MIN_VALUE,16*Number.EPSILON*Math.max(input.measurement.baseline_wh,input.measurement.candidate_wh,input.measurement.overhead_wh,uncertainty.bound_wh,uncertainty.minimum_net_wh));
    effect={net_difference_wh:comparison.net_wh,declared_error_bound_wh:uncertainty.bound_wh,arithmetic_allowance_wh:roundoff,lower_bound_wh:comparison.net_wh-uncertainty.bound_wh-roundoff,upper_bound_wh:comparison.net_wh+uncertainty.bound_wh+roundoff,minimum_net_wh:uncertainty.minimum_net_wh};
    if(comparison.net_wh<=0)check('net_effect','RETAIN_BASELINE','The comparable full batch is a non-win. Keep the result and baseline.',effect);
    else if(effect.lower_bound_wh<=effect.minimum_net_wh)check('net_effect','EVIDENCE_INSUFFICIENT','The conservative net difference does not exceed the declared advancement threshold.',effect);
    else check('net_effect','PASS','The declared net difference and uncertainty clear the threshold for owner review only.',effect);
  }else if(comparison&&comparison.net_wh!==null&&comparison.net_wh<=0)check('net_effect','RETAIN_BASELINE','The comparable full batch is a non-win, even while other evidence is incomplete.');
  const decision=['DATA_INVALID','CONSTRAINT_FAILED','EVIDENCE_INSUFFICIENT','RETAIN_BASELINE'].find(status=>checks.some(c=>c.status===status))||'CANDIDATE_FOR_REVIEW';
  return {schema:ENERGY_REVIEW_SCHEMA,reviewed_at:reviewedAt,decision,comparison,checks,expected_effect:effect,evidence_refs:[...refs],
    evidence_scope:'OWNER_ENTERED_HISTORICAL_OBSERVATIONS',source_verification:'REFERENCES_RECORDED_NOT_INDEPENDENTLY_VERIFIED',
    fallback:{action:'RETAIN_BASELINE',baseline_id:fallback.baseline_id||null,trigger:fallback.trigger||null},actuation_authorized:false};
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
