(()=>{
'use strict';
const transform=(p,{x=0,y=0,scale=1}={})=>({x:(p.x-.5)*scale+.5+x,y:(p.y-.5)*scale+.5+y});
function agreement(a,b,t,w,h){
 if(!a||!b||!(w>0)||!(h>0))return null;
 const q=transform(b,t),d=Math.hypot((q.x-a.x)*w,(q.y-a.y)*h)/Math.hypot(w,h);
 return {within:d<=.05+1e-12,d};
}
if(typeof module!=='undefined'&&module.exports)module.exports={transform,agreement};
if(typeof document==='undefined')return;
const $=id=>document.getElementById(id);
const root=$('landmark-lab'), art=$('overlay-art');
if(!root||!art)return;
const names=['Left eye (as viewed)','Right eye (as viewed)','Nose tip','Mouth center'];
let marks=[[],[]], sources=['',''], images=[$('landmark-image-a'),$('landmark-image-b')];
const stage=$('landmark-stage-marks'), panels=[$('landmark-view-a'),$('landmark-view-b')];
const fx=$('landmark-x'),fy=$('landmark-y'), feature=$('landmark-feature'), layer=$('landmark-layer');
const clamp=(n)=>Math.min(1,Math.max(0,n));
function star(parent,p,txt,cls,side){
 if(p.x<0||p.x>1||p.y<0||p.y>1)return;
 const s=document.createElement('span');
 s.className='landmark-star '+cls+' landmark-layer-'+side;s.textContent='★'+txt;
 s.style.left=p.x*100+'%';s.style.top=p.y*100+'%';parent.append(s);
}
function draw(){
 const t={x:Number($('overlay-x').value)/100,y:Number($('overlay-y').value)/100,scale:Number($('overlay-scale').value)/100};
 const w=art.clientWidth,h=art.clientHeight;
 const status=$('landmark-status'),list=$('landmark-list');
 list.replaceChildren();stage.replaceChildren();panels.forEach((p,i)=>$('landmark-stars-'+i).replaceChildren());
 let paired=0,within=0;
 for(let k=0;k<names.length;k++){
  const a=marks[0][k],b=marks[1][k],r=agreement(a,b,t,w,h);
  if(r){paired++;if(r.within)within++;}
  const note=r?(r.within?'Within tolerance':'Outside tolerance'):(a||b?'Mark the other layer':'Not marked');
  const row=document.createElement('li');row.textContent=names[k]+': '+note;list.append(row);
  const cls=r?(r.within?'landmark-hit':'landmark-miss'):'landmark-unpaired';
  if(a){star($('landmark-stars-0'),a,k+1,cls,0);star(stage,a,'A'+(k+1),cls,0);}
  if(b){star($('landmark-stars-1'),b,k+1,cls,1);star(stage,transform(b,t),'B'+(k+1),cls,1);}
 }
 status.textContent=paired>=3?Math.round(100*within/paired)+'% geometric alignment ('+within+' of '+paired+' paired marks within tolerance).':paired+' of 4 landmarks paired. Mark at least 3 pairs to see a percentage.';
}
function sync(){
 const live=['overlay-image-a','overlay-image-b'].map(id=>$(id));
 const next=live.map(img=>img.getAttribute('src')||'');
 if(next.some((v,i)=>v!==sources[i])){
  marks=[[],[]];sources=next;
  for(let i=0;i<2;i++){
   images[i].alt=live[i].alt||'';
   if(next[i])images[i].setAttribute('src',next[i]);else images[i].removeAttribute('src');
  }
 }
 for(const field of [fx,fy])field.disabled=!sources[Number(layer.value)];
 $('landmark-place').disabled=fx.disabled;
 draw();
}
function selectPoint(){
 const p=marks[Number(layer.value)][Number(feature.value)];
 fx.value=String(p?Math.round(p.x*100):50);fy.value=String(p?Math.round(p.y*100):50);sync();
}
function place(side,k,x,y){
 if(!sources[side]||!(k>=0&&k<names.length))return;
 marks[side][k]={x:clamp(x),y:clamp(y)};draw();
}
panels.forEach((p,side)=>p.addEventListener('click',event=>{
 const rect=p.getBoundingClientRect();
 if(!p.clientWidth||!p.clientHeight)return;
 const x=clamp((event.clientX-rect.left-p.clientLeft)/p.clientWidth),y=clamp((event.clientY-rect.top-p.clientTop)/p.clientHeight);
 layer.value=String(side);fx.value=String(Math.round(100*x));fy.value=String(Math.round(100*y));
 place(side,Number(feature.value),x,y);sync();
}));
layer.addEventListener('change',selectPoint);feature.addEventListener('change',selectPoint);
$('landmark-place').addEventListener('click',()=>place(Number(layer.value),Number(feature.value),Number(fx.value)/100,Number(fy.value)/100));
$('landmark-clear').addEventListener('click',()=>{marks=[[],[]];selectPoint();});
for(const id of ['overlay-x','overlay-y','overlay-scale','overlay-reset','overlay-use','overlay-history','overlay-swap','overlay-base','overlay-top']){
 const field=$(id); const event=id==='overlay-base'||id==='overlay-top'?'change':['overlay-x','overlay-y','overlay-scale'].includes(id)?'input':'click';
 field.addEventListener(event,sync);
}
if(typeof ResizeObserver==='function')new ResizeObserver(draw).observe(art);
sync();
})();
