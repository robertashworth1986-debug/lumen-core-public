(function(){
'use strict';
const pairs=window.ATLAS_PAIRS||[], $=id=>document.getElementById(id);
const make=(tag,txt)=>{const el=document.createElement(tag); if(txt!==undefined)el.textContent=txt;return el;};
const link=(txt,url)=>{const el=make('a',txt);el.href=url;el.target='_blank';el.rel='noopener noreferrer';return el;};
const matches=(pair,query,cat)=> (!cat||pair.tag===cat)&&query.trim().toLowerCase().split(/\s+/).every(term=>pair.people.map(p=>p.name.toLowerCase()).join(' ').includes(term));
const rotate=(i,delta,n)=>(i+delta+n)%n;
const pick=(i,n,random=Math.random)=>n<2?i:rotate(i,1+Math.floor(random()*(n-1)),n);
if (typeof module!=='undefined') module.exports={matches,rotate,pick};
let active=0, visible=pairs;
const title=p=>p.people.map(x=>x.name).join(' / ');
const sharedId=hash=>/^#pair-([1-9][0-9]*)$/.exec(hash)?.[1];
const pairUrl=id=>window.location.origin+'/apps/doppelganger/#pair-'+id;
const defaultShareStatus='Opens this exact editorial comparison.';
function readSharedPair(){
 const i=pairs.findIndex(p=>String(p.id)===sharedId(window.location.hash));
 if(i<0)return false;
 $('search').value='';$('category').value='';
 visible=pairs;active=i;
 return true;
}
function show(){
 const n=visible.length;
 for(const id of ['shuffle','previous','next']) $(id).disabled=n<2;
 $('position').textContent=n?'PAIR '+(active+1)+' / '+n:'NO MATCHES';
 $('count').textContent=n+' '+(n===1?'pair':'pairs');
 const p=visible[active];
 $('pair-share').hidden=!p;
 $('pair-url').value=p?pairUrl(p.id):'';
 $('pair-status').textContent=defaultShareStatus;
 $('tag').textContent=p?.tag||'';
 $('note').textContent=p?.note||'Try another name or category.';
 const grid=make('div');grid.className='duo';
 if(p)for(const x of p.people){
   const f=make('figure'),img=make('img'),cap=make('figcaption'),credit=make('details');
   img.alt='Portrait of '+x.name;img.src=x.photo;img.width=x.width;img.height=x.height;
   img.addEventListener('error',()=>{const missing=make('p','Photo unavailable.');img.replaceWith(missing);},{once:true});
   credit.append(make('summary','Photo credit'),link(x.title,x.source),' by '+x.author+' · ',link(x.license,x.licenseUrl),' · resized and converted to WebP.');
   cap.append(make('strong',x.name),credit);f.append(img,cap);grid.append(f);
 }
 $('comparison').replaceChildren(grid);
 const options=visible.map((candidate,i)=>{const btn=make('button');btn.type='button';btn.setAttribute('aria-pressed',String(i===active));btn.append(make('strong',title(candidate)),make('span',candidate.tag));btn.addEventListener('click',()=>{active=i;show();document.querySelector('.stage').scrollIntoView({block:'start'});$('position').tabIndex=-1;$('position').focus({preventScroll:true});});return btn;});
 $('list').replaceChildren(...options);
}
for(const id of ['search','category']) $(id).addEventListener(id==='search'?'input':'change',()=>{visible=pairs.filter(p=>matches(p,$('search').value,$('category').value));active=0;show();});
$('next').onclick=()=>{active=rotate(active,1,visible.length);show();};
$('previous').onclick=()=>{active=rotate(active,-1,visible.length);show();};
$('shuffle').onclick=()=>{active=pick(active,visible.length);show();};
$('pair-copy').onclick=async()=>{
 const field=$('pair-url'),value=field.value,status=$('pair-status');
 if(!value)return;
 try{
  await window.navigator.clipboard.writeText(value);
  if(field.value===value)status.textContent='Pair link copied.';
 }catch{
  if(field.value===value){field.focus();field.select();status.textContent='Copy the selected link manually.';}
 }
};
window.addEventListener('hashchange',()=>{if(readSharedPair()){show();}});
const openedSharedPair=readSharedPair();
show();
if(openedSharedPair)document.querySelector('.stage')?.scrollIntoView({block:'start'});
})();
