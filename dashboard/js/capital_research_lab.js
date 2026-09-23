import {nonnegative, runway, fundingGap, dilution, debtPayment} from './capital_math.js';

const $ = (q) => document.querySelector(q);
const $$ = (q) => [...document.querySelectorAll(q)];
const colors = {Revenue:'#34d399',Grant:'#22d3ee',Equity:'#a855f7',Debt:'#f4bc67',Support:'#82aaff'};
const money = new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0});
const paymentMoney = new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2});
const storageKey = 'lumencore.capital-lab.notes.v1';
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
let data, activeTab='command', paused=reduced.matches, scenarioMode='empty', orbit;

function el(tag, text, className) {
  const node=document.createElement(tag);
  if(text!==undefined) node.textContent=text;
  if(className) node.className=className;
  return node;
}
function link(source) {
  const a=el('a',`${source.title} ↗`); a.href=source.url; a.target='_blank'; a.rel='noopener noreferrer'; return a;
}
function detailButton(route, text='Inspect conditions →') {
  const b=el('button',text,'text-button'); b.addEventListener('click',()=>showDetail(route)); return b;
}
function showTab(name, focus=false) {
  if(!['command','sources','scenarios','notebook'].includes(name))return;
  activeTab=name;
  $$('.tab-panel').forEach(panel=>panel.hidden=panel.id!==`tab-${name}`);
  $$('[data-tab]').forEach(button=>{
    const current=button.dataset.tab===name;
    button.classList.toggle('active',current);
    if(current)button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current');
  });
  history.replaceState(null,'',`#${name}`);
  if(focus){ const heading=$(`#tab-${name} h1`); heading.tabIndex=-1; heading.focus({preventScroll:true}); window.scrollTo({top:0,behavior:'instant'}); }
  if(name==='command')orbit?.resize();
}
function showDetail(route) {
  const box=$('#detail-content'); box.replaceChildren();
  box.append(el('span',route.type.toUpperCase(),'eyebrow cyan'),el('h2',route.name),el('p',route.summary),el('span',route.amount,'pill'));
  box.append(el('h3','Conditions to establish'));
  const list=el('ul'); route.requirements.forEach(item=>list.append(el('li',item))); box.append(list);
  box.append(el('h3','Next research action'),el('p',route.next),el('h3','Timing and application state'),el('p',`${route.timing}. ${route.application_status}.`),el('p',route.limit,'source-note'),el('h3','Inspect the sources'));
  route.sources.forEach(source=>{const p=el('p');p.append(link(source),el('br'),el('small',source.kind));box.append(p);});
  box.append(el('p',`Reviewed ${new Date(data.reviewed_at).toLocaleDateString('en-US',{dateStyle:'long'})}. Verify current terms directly before acting.`,'fine'));
  $('#route-detail').showModal();
}
function renderRoutes() {
  const query=$('#route-search').value.trim().toLowerCase(), type=$('#route-type').value;
  const rows=data.routes.filter(route=>(type==='All'||route.type===type)&&JSON.stringify(route).toLowerCase().includes(query));
  $('#filter-count').textContent=`${rows.length} of ${data.routes.length} routes`;
  const grid=$('#route-cards');grid.replaceChildren();
  rows.forEach(route=>{
    const card=el('article',undefined,'panel source-card'); card.style.setProperty('--route-color',colors[route.type]);
    const meta=el('div',undefined,'source-meta');meta.append(el('span',route.type.toUpperCase(),'eyebrow'),el('span',route.status,'pill'));
    const bottom=el('div',undefined,'bottom');bottom.append(detailButton(route),link({title:'Official source',url:route.sources[0].url}));
    if(route.type==='Revenue')bottom.lastChild.textContent='Existing offer ↗';
    card.append(meta,el('h2',route.name),el('div',route.amount,'amount'),el('p',route.summary),el('p',`Next: ${route.next}`),bottom);grid.append(card);
  });
  if(!rows.length)grid.append(el('p','No routes match these filters. Try another term or choose All.','panel'));
}
function renderResearch() {
  const date=new Date(data.reviewed_at);
  $('#review-date').textContent=date.toLocaleDateString('en-US',{month:'short',day:'2-digit',year:'numeric'}).toUpperCase();
  $('#footer-date').textContent=date.toLocaleDateString('en-US',{dateStyle:'long'});
  $('#route-count').textContent=String(data.routes.length).padStart(2,'0'); $('#nav-count').textContent=data.routes.length;
  const days=Math.max(0,Math.floor((Date.now()-date.getTime())/86400000));
  $('#freshness').textContent=days>7?`This snapshot is ${days} days old. Recheck official sources for current dates, terms and availability.`:'Reviewed public-source snapshot. This page is not a live application-status feed.';
  Object.entries(colors).forEach(([type,color])=>{
    const button=el('button');const dot=el('i');dot.style.background=color;button.append(dot,document.createTextNode(type));
    button.addEventListener('click',()=>{$('#route-type').value=type;renderRoutes();showTab('sources',true);});$('#route-legend').append(button);
  });
  data.routes.filter(route=>['pilot','ec-impact','assisttn'].includes(route.id)).forEach(route=>{
    const card=el('article',undefined,'priority-card');card.append(el('span',route.priority.toUpperCase(),'eyebrow cyan'),el('h3',route.name),el('p',route.next),detailButton(route));$('#priority-cards').append(card);
  });
  data.session_questions.forEach(question=>$('#session-questions').append(el('li',question)));
  data.readiness.forEach((item,index)=>{
    const label=el('label',undefined,'check-row'),input=el('input');input.type='checkbox';input.dataset.ready=index;
    input.addEventListener('change',()=>{updateReadiness();unsavedNotes();});label.append(input,el('span',item));$('#readiness').append(label);
  });
  renderRoutes();
}
function assumptions(){return Object.fromEntries($$('[data-input]').map(input=>[input.dataset.input,input.value]));}
function calculate() {
  const values=assumptions();
  const current=runway(values.cash,values.burn),gap=fundingGap(values.cash,values.burn,values.horizon,values.oneoff,values.fees);
  $('#runway-result').textContent=current===null?'—':current===Infinity?'No net burn':`${current.toFixed(1)} months`;
  $('#gap-result').textContent=gap===null?'—':money.format(gap);
  const share=dilution(values.raise,values.premoney);
  $('#dilution-result').textContent=share===null?'—':`${(share*100).toFixed(1)}%`;
  $('#retained-result').textContent=share===null?'—':`${((1-share)*100).toFixed(1)}%`;
  const bar=$('#ownership-bar');bar.replaceChildren();if(share!==null){const span=el('span');span.style.width=`${share*100}%`;bar.append(span);}
  const monthly=debtPayment(values.principal,values.apr,values.term);
  $('#payment-result').textContent=monthly===null?'—':paymentMoney.format(monthly);
  $('#interest-result').textContent=monthly===null?'—':paymentMoney.format(Math.max(0,monthly*Number(values.term)-Number(values.principal)));
  const cash=nonnegative(values.cash),burn=nonnegative(values.burn), sensitivity=$('#sensitivity');sensitivity.replaceChildren();
  if(cash!==null&&burn!==null&&burn>0){
    sensitivity.append(el('h3','Runway sensitivity · constant monthly burn'));
    const max=runway(cash,burn*.8);
    [['Burn −20%',.8],['Your assumption',1],['Burn +20%',1.2]].forEach(([label,factor])=>{
      const months=runway(cash,burn*factor),row=el('div',undefined,'sensitivity-row'),track=el('div'),fill=el('i');
      fill.style.width=`${max>0?100*months/max:0}%`;track.append(fill);row.append(el('span',label),track,el('strong',`${months.toFixed(1)} mo`));sensitivity.append(row);
    });
  }else sensitivity.append(el('p','Supply cash and positive monthly burn to compare runway under different burn assumptions.','fine'));
  const supplied=Object.values(values).some(value=>value.trim()!=='');
  $('#scenario-mode').textContent=!supplied?'NO INPUTS SUPPLIED':scenarioMode==='example'?'TEACHING EXAMPLE · NOT COMPANY ACTUALS':'YOUR ASSUMPTIONS · NOT VERIFIED ACTUALS';
}
function download(filename,text,type='application/json') {
  const url=URL.createObjectURL(new Blob([text],{type})),a=el('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function updateReadiness(){const total=$$('[data-ready]:checked').length;$('#ready-count').textContent=`${total} of ${data.readiness.length} items self-confirmed. Not independently verified.`;}
function unsavedNotes(){$('#notes-status').textContent='Unsaved changes. Save in this browser or download your working brief.';}
function workingNotes(){return {schema:'lumencore.capital-notes.v1',saved_at:new Date().toISOString(),notes:$('#session-notes').value,use_of_funds:$('#use-funds').value,next_action:$('#next-action').value,self_confirmed:$$('[data-ready]:checked').map(input=>data.readiness[Number(input.dataset.ready)])};}
function restoreNotes(){
  try{
    const raw=localStorage.getItem(storageKey);if(!raw)return;const saved=JSON.parse(raw);if(saved.schema!=='lumencore.capital-notes.v1')return;
    $('#session-notes').value=typeof saved.notes==='string'?saved.notes:'';$('#use-funds').value=typeof saved.use_of_funds==='string'?saved.use_of_funds:'';$('#next-action').value=typeof saved.next_action==='string'?saved.next_action:'';
    $$('[data-ready]').forEach(input=>input.checked=Array.isArray(saved.self_confirmed)&&saved.self_confirmed.includes(data.readiness[Number(input.dataset.ready)]));
    $('#notes-status').textContent=`Restored notes saved ${new Date(saved.saved_at).toLocaleString()}. They remain in this browser. Export a backup before changing browsers.`;updateReadiness();
  }catch{$('#notes-status').textContent='Saved notes could not be restored. New notes can still be exported as a working brief.';}
}
function bindUI(){
  $$('[data-tab]').forEach(button=>button.addEventListener('click',()=>showTab(button.dataset.tab)));
  $$('[data-go]').forEach(button=>button.addEventListener('click',()=>showTab(button.dataset.go,true)));
  $('#close-detail').addEventListener('click',()=>$('#route-detail').close());
  $('#route-search').addEventListener('input',renderRoutes);$('#route-type').addEventListener('change',renderRoutes);
  $$('[data-input]').forEach(input=>input.addEventListener('input',()=>{scenarioMode='user';calculate();}));
  $('#load-example').addEventListener('click',()=>{
    const sample={cash:25000,burn:5000,horizon:12,oneoff:10000,fees:2500,raise:100000,premoney:900000,principal:50000,apr:10,term:60};
    $$('[data-input]').forEach(input=>input.value=sample[input.dataset.input]);scenarioMode='example';calculate();
  });
  $('#clear-scenario').addEventListener('click',()=>{$$('[data-input]').forEach(input=>input.value='');scenarioMode='empty';calculate();});
  $('#export').addEventListener('click',()=>download(`lumencore-capital-research-${data.reviewed_at.slice(0,10)}.json`,JSON.stringify(data,null,2)));
  $$('#tab-notebook textarea').forEach(input=>input.addEventListener('input',unsavedNotes));
  $('#save-notes').addEventListener('click',()=>{
    try{localStorage.setItem(storageKey,JSON.stringify(workingNotes()));$('#notes-status').textContent=`Saved in this browser at ${new Date().toLocaleTimeString()}. No notes were sent. Download a working brief for your own backup.`;}
    catch{$('#notes-status').textContent='This browser did not permit local saving. Download the working brief to keep a copy.';}
  });
  $('#export-notes').addEventListener('click',()=>{
    const notes=workingNotes(),values=assumptions();
    const text=['# LumenCore — EC capital working brief',`Exported: ${notes.saved_at}`,'','## Session notes',notes.notes||'(Not supplied)','','## Use of funds',notes.use_of_funds||'(Not supplied)','','## Next action',notes.next_action||'(Not supplied)','','## Readiness self-check (not independently verified)',...data.readiness.map(item=>`- [${notes.self_confirmed.includes(item)?'x':' '}] ${item}`),'','## Scenario assumptions',`Input mode: ${$('#scenario-mode').textContent}`,...Object.entries(values).map(([key,value])=>`- ${key}: ${value||'(Not supplied)'}`),'','## Research snapshot',`Reviewed: ${data.reviewed_at}`,...data.routes.map(route=>`- ${route.name}: ${route.sources.map(s=>s.url).join(' | ')}`),'','Program listings do not establish eligibility, approval or committed funds.'].join('\n');
    download(`lumencore-capital-working-brief-${new Date().toISOString().slice(0,10)}.md`,text,'text/markdown;charset=utf-8');
    $('#notes-status').textContent='Working-brief download requested. It includes your notes and any scenario assumptions on this page.';
  });
  $('#motion').addEventListener('click',()=>{paused=!paused;setMotion();});
  reduced.addEventListener('change',event=>{paused=event.matches;setMotion();});
  window.addEventListener('hashchange',()=>showTab(location.hash.slice(1)));
  setMotion();
}
function setMotion(){$('#motion').textContent=paused?'Resume motion':'Pause motion';$('#motion').setAttribute('aria-pressed',String(paused));document.body.classList.toggle('low-motion',paused);}

// Decorative rendering is bounded and stops while hidden. It represents no financial metric.
function startStarfield(){
  const canvas=$('#starfield'),ctx=canvas.getContext('2d');if(!ctx)return;
  let width=0,height=0,last=0,phase=0,dirty=true;
  const stars=Array.from({length:75},(_,i)=>({x:((i*73+19)%997)/997,y:((i*137+43)%991)/991,r:i%4===0?1.2:.6}));
  function resize(){const dpr=Math.min(devicePixelRatio||1,1.5);width=innerWidth;height=innerHeight;canvas.width=width*dpr;canvas.height=height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);dirty=true;}
  resize();window.addEventListener('resize',resize);
  function draw(time){
    requestAnimationFrame(draw);if(document.hidden||time-last<50||paused&&!dirty)return;last=time;dirty=false;if(!paused)phase+=.004;
    ctx.clearRect(0,0,width,height);for(const [i,star] of stars.entries()){ctx.globalAlpha=.12+.23*(.5+.5*Math.sin(phase+i));ctx.fillStyle=i%3?'#74dff5':'#b391f7';ctx.beginPath();ctx.arc(star.x*width,star.y*height,star.r,0,Math.PI*2);ctx.fill();}ctx.globalAlpha=1;
  }requestAnimationFrame(draw);
}
async function startOrbit(){
  const canvas=$('#capital-orbit');
  try{
    const THREE=await import('../build_week/prooflock_console/three.module.min.js');
    const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));
    const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(42,1,.1,100);camera.position.set(0,.3,7.6);
    const group=new THREE.Group();scene.add(group);
    const rings=[];
    [0x22d3ee,0xa855f7,0x34d399].forEach((color,i)=>{
      const ring=new THREE.Mesh(new THREE.TorusGeometry(1.72+i*.19,.009,6,140),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.48}));
      ring.rotation.set(.6+i*.55,.1+i*.55,.2+i*.4);group.add(ring);rings.push(ring);
    });
    const nodes=Object.values(colors).map((color,i)=>{const node=new THREE.Mesh(new THREE.SphereGeometry(.046,10,8),new THREE.MeshBasicMaterial({color}));group.add(node);return node;});
    const positions=new Float32Array(180*3);for(let i=0;i<180;i++){const a=i*2.399963,r=1.2+(i%41)/17;positions[i*3]=Math.cos(a)*r;positions[i*3+1]=Math.sin(a)*r*.73;positions[i*3+2]=Math.sin(i*1.3)*1.5;}
    const pointsGeometry=new THREE.BufferGeometry();pointsGeometry.setAttribute('position',new THREE.BufferAttribute(positions,3));
    const points=new THREE.Points(pointsGeometry,new THREE.PointsMaterial({color:0x83b6e8,size:.017,transparent:true,opacity:.55}));group.add(points);
    let dirty=true,last=0,phase=0;
    function resize(){const rect=canvas.parentElement.getBoundingClientRect();if(rect.width<=0||rect.height<=0)return;renderer.setSize(rect.width,rect.height,false);camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();dirty=true;}
    orbit={resize};new ResizeObserver(resize).observe(canvas.parentElement);resize();
    function frame(time){
      requestAnimationFrame(frame);if(document.hidden||activeTab!=='command'||time-last<33||paused&&!dirty)return;last=time;dirty=false;if(!paused)phase+=.004;
      rings.forEach((ring,i)=>ring.rotation.z=.2+i*.4+phase*(i%2?-.2:.3));
      nodes.forEach((node,i)=>{const angle=i*Math.PI*2/5+phase*(.4+i*.06),r=1.72+(i%3)*.19;node.position.set(Math.cos(angle)*r,Math.sin(angle)*r*.7,Math.sin(angle+i)*.65);});
      points.rotation.y=phase*.04;renderer.render(scene,camera);
    }requestAnimationFrame(frame);
  }catch{
    // A static SVG fallback keeps the diagram visible without WebGL or module support.
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 500 280');svg.setAttribute('aria-hidden','true');svg.style.cssText='width:100%;height:100%';
    [0,1,2].forEach(i=>{const ellipse=document.createElementNS(svg.namespaceURI,'ellipse');Object.entries({cx:250,cy:140,rx:150+i*10,ry:58+i*12,fill:'none',stroke:Object.values(colors)[i],opacity:.6,transform:`rotate(${i*55-35} 250 140)`}).forEach(([k,v])=>ellipse.setAttribute(k,String(v)));svg.append(ellipse);});canvas.replaceWith(svg);
  }
}
async function init(){
  try{
    const response=await fetch('./assets/capital_research.json',{cache:'no-cache'});if(!response.ok)throw Error('Research snapshot unavailable');data=await response.json();
    if(data.schema!=='lumencore.capital_research.v1'||!Array.isArray(data.routes))throw Error('Research snapshot format is not supported');
    renderResearch();bindUI();restoreNotes();calculate();$('#load-state').hidden=true;$('#workspace').hidden=false;showTab(location.hash.slice(1)||'command');startStarfield();startOrbit();
  }catch(error){$('#load-state').textContent=`The research snapshot could not load. Please reload this page. ${error.message}`;}
}
init();
