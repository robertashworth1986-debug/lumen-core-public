(()=>{
'use strict';
const history=[
 {name:'Robert Cornelius', era:'1839 self-portrait',photo:'photos/loc-cornelius-1839.webp',author:'Robert Cornelius',source:'https://www.loc.gov/pictures/item/2004664436/',scan:'https://commons.wikimedia.org/wiki/File:RobertCornelius.jpg',rights:'Public domain'},
 {name:'Abraham Lincoln',era:'1846 or 1847 portrait',photo:'photos/loc-lincoln-1846.webp',author:'Attributed to Nicholas H. Shepherd',source:'https://www.loc.gov/item/2004664400/',scan:'https://commons.wikimedia.org/wiki/File:Abraham_Lincoln_by_Nicholas_Shepherd,_1846.jpg',rights:'Public domain'}
];
const pairs=window.ATLAS_PAIRS||[];
const modern=[...new Map(pairs.flatMap(p=>p.people).map(p=>[p.photo,p])).values()];
const $=id=>document.getElementById(id);
const base=$('overlay-base'),top=$('overlay-top'), bottomImg=$('overlay-image-a'), topImg=$('overlay-image-b');
if(!base||!top||modern.length<2)return;
const photos=new Map([...modern,...history].map(p=>[p.photo,p]));
const title=p=>p.era?p.name+' · '+p.era:p.name;
const label=(p,fallback)=>p?title(p):fallback;
const node=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
const link=(text,href)=>{const a=node('a',text);a.href=href;return a;};
for(const sel of [base,top]){
 for(const [label,group] of [['Portrait gallery',modern],['Early photography',history]]){
  const opts=node('optgroup');opts.label=label;
  for(const p of group){const o=node('option',title(p));o.value=p.photo;opts.append(o);}sel.append(opts);
 }
}
function showCredit(out,p,label){
 out.replaceChildren();
 if(!p)return;
 const heading=node('strong',label+' · '+title(p));
 out.append(heading,' — '+p.author+' · ',link(p.scan?'Library of Congress item':p.title,p.source),' · ');
 if(p.scan)out.append(link('Scan source',p.scan),' · '+p.rights+'. Resized to WebP.');
 else out.append(link(p.license,p.licenseUrl),'. Resized to WebP.');
}
const defaults={opacity:50,x:0,y:0,scale:100};
const controls=Object.fromEntries(Object.keys(defaults).map(k=>[k,$('overlay-'+k)]));
const range=(k)=>Number(controls[k].value);
function applyAlignment(){
 const opacity=range('opacity'),x=range('x'),y=range('y'),scale=range('scale');
 $('overlay-art').style.setProperty('--overlay-opacity',String(opacity/100));
 $('overlay-art').style.setProperty('--overlay-x',x+'%');
 $('overlay-art').style.setProperty('--overlay-y',y+'%');
 $('overlay-art').style.setProperty('--overlay-scale',String(scale/100));
 for(const k of Object.keys(controls))$('overlay-'+k+'-readout').textContent=controls[k].value+'%';
}
function clearVote(){
 for(const btn of $('overlay-verdicts').querySelectorAll('button'))btn.setAttribute('aria-pressed','false');
 $('overlay-opinion').textContent='Make your own call. No result is calculated or saved.';
}
function setImage(img,p,loading){
 if(!p){img.hidden=true;img.removeAttribute('src');img.alt='';return;}
 img.alt='Portrait of '+p.name;
 if(img.getAttribute('src')!==p.photo){img.hidden=false;loading.hidden=true;img.setAttribute('src',p.photo);}
}
function render(reset=true){
 const a=photos.get(base.value),b=photos.get(top.value);
 if(reset){for(const k of Object.keys(defaults))controls[k].value=String(defaults[k]);clearVote();}
 setImage(bottomImg,a,$('overlay-missing-a'));setImage(topImg,b,$('overlay-missing-b'));
 showCredit($('overlay-credit-base'),a,'Base');showCredit($('overlay-credit-top'),b,'Top');
 $('overlay-names').textContent=label(a,'Choose a base portrait')+' / '+label(b,'Choose a top portrait');
 applyAlignment();
}
for(const [img,id] of [[bottomImg,'overlay-missing-a'],[topImg,'overlay-missing-b']]){
 img.addEventListener('error',()=>{img.hidden=true;$(id).hidden=false;});
 img.addEventListener('load',()=>{img.hidden=false;$(id).hidden=true;});
}
function useComparison(){
 const current=document.querySelectorAll('#comparison figure img');
 const a=current[0]?.getAttribute('src'),b=current[1]?.getAttribute('src');
 if(photos.has(a)&&photos.has(b)){base.value=a;top.value=b;render();return true;}
 return false;
}
function loadFeatured(){if(!useComparison())$('overlay-opinion').textContent='Select a featured gallery pair first.';}
$('overlay-use').addEventListener('click',loadFeatured);
$('feature-overlay')?.addEventListener('click',loadFeatured);
$('overlay-history').addEventListener('click',()=>{base.value=history[0].photo;top.value=history[1].photo;render();});
$('overlay-swap').addEventListener('click',()=>{const a=base.value;base.value=top.value;top.value=a;render();});
$('overlay-reset').addEventListener('click',()=>{for(const k of Object.keys(defaults))controls[k].value=String(defaults[k]);applyAlignment();clearVote();});
for(const sel of [base,top])sel.addEventListener('change',()=>render());
for(const field of Object.values(controls))field.addEventListener('input',applyAlignment);
for(const btn of $('overlay-verdicts').querySelectorAll('button')){
 btn.addEventListener('click',()=>{
  clearVote();btn.setAttribute('aria-pressed','true');
  $('overlay-opinion').textContent='Your impression: '+btn.textContent+'. Visual opinion only, not an identity result.';
 });
}
// Starting state reuses the current featured pair without adding storage or requests.
base.value=modern[0].photo;top.value=modern[1].photo;
if(!useComparison())render();
})();
