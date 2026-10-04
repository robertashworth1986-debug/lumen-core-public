/**
 * Dependency-free mathematical data and SVGs. Coordinates are mathematical,
 * not image-generation approximations. Public SVG inputs are bounded numbers
 * or an allow-listed solid name; arbitrary text is never interpolated.
 */
export const PHI = (1 + Math.sqrt(5)) / 2;
export const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
export const PLATONIC_NAMES = Object.freeze(['tetrahedron', 'cube', 'octahedron', 'dodecahedron', 'icosahedron']);
const EPS = 1e-9;
const COLORS = { ink: '#e8edf4', muted: '#9faec2', gold: '#e7bb71', cyan: '#6bd8de', blue: '#587eb7', bg: '#0c1421' };
const subtract = (a, b) => a.map((v, i) => v - b[i]);
const dot = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
const cross = (a, b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
const norm = a => Math.hypot(...a);
const unit = a => a.map(v => v / norm(a));
const distance = (a, b) => norm(subtract(a, b));
function bounded(value, fallback, lo, hi, name, integer = false) {
  const n = value === undefined ? fallback : value;
  if (typeof n !== 'number' || !Number.isFinite(n) || n < lo || n > hi || (integer && !Number.isInteger(n))) {
    throw new RangeError(`${name} must be ${integer ? 'an integer' : 'a finite number'} in [${lo}, ${hi}]`);
  }
  return n;
}
const fmt = n => { if (!Number.isFinite(n)) throw new RangeError('Non-finite SVG coordinate'); return Number(n.toFixed(5)).toString(); };
function frame(width, height, title, description, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${fmt(width)} ${fmt(height)}" role="img" aria-label="${title}" style="width:100%;height:auto;display:block"><title>${title}</title><desc>${description}</desc><rect width="100%" height="100%" rx="18" fill="${COLORS.bg}"/>${body}</svg>`;
}
function line(a, b, color, width = 1.5, extra = '') {
  return `<line x1="${fmt(a[0])}" y1="${fmt(a[1])}" x2="${fmt(b[0])}" y2="${fmt(b[1])}" stroke="${color}" stroke-width="${fmt(width)}" ${extra}/>`;
}
function circle(p, radius, color) { return `<circle cx="${fmt(p[0])}" cy="${fmt(p[1])}" r="${fmt(radius)}" fill="${color}"/>`; }
function text(x, y, content, color = COLORS.muted, size = 12) {
  // Private helper: content only receives fixed labels or finite formatted numbers.
  return `<text x="${fmt(x)}" y="${fmt(y)}" fill="${color}" font-family="system-ui,sans-serif" font-size="${fmt(size)}">${content}</text>`;
}

function rawVertices(name) {
  const out = [], signs = [-1, 1];
  if (name === 'tetrahedron') return [[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]];
  if (name === 'cube' || name === 'dodecahedron') for (const x of signs) for (const y of signs) for (const z of signs) out.push([x,y,z]);
  if (name === 'octahedron') for (let i=0;i<3;i++) for (const s of signs) { const p=[0,0,0]; p[i]=s; out.push(p); }
  if (name === 'icosahedron') for (const a of signs) for (const b of signs) out.push([0,a,b*PHI],[a,b*PHI,0],[b*PHI,0,a]);
  if (name === 'dodecahedron') for (const a of signs) for (const b of signs) out.push([0,a/PHI,b*PHI],[a/PHI,b*PHI,0],[b*PHI,0,a/PHI]);
  return out;
}

// Enumerate supporting planes. Coplanar triples coalesce to one ordered polygon.
// The maximum input has only 20 vertices, making exhaustive enumeration bounded.
function convexFaces(vertices) {
  const found = new Map();
  for (let i=0;i<vertices.length;i++) for (let j=i+1;j<vertices.length;j++) for (let k=j+1;k<vertices.length;k++) {
    let normal = cross(subtract(vertices[j],vertices[i]), subtract(vertices[k],vertices[i]));
    if (norm(normal) < EPS) continue;
    normal = unit(normal);
    const offsets = vertices.map(p => dot(normal,subtract(p,vertices[i])));
    if (offsets.some(v=>v>EPS) && offsets.some(v=>v < -EPS)) continue;
    const indices = offsets.flatMap((v,index)=>Math.abs(v)<EPS ? [index] : []);
    const key = indices.join(',');
    if (found.has(key)) continue;
    const center = [0,1,2].map(axis=>indices.reduce((s,index)=>s+vertices[index][axis],0)/indices.length);
    if (dot(normal,center)<0) normal=normal.map(v=>-v);
    const u=unit(subtract(vertices[indices[0]],center)), v=cross(normal,u);
    indices.sort((a,b)=>Math.atan2(dot(subtract(vertices[a],center),v),dot(subtract(vertices[a],center),u))-Math.atan2(dot(subtract(vertices[b],center),v),dot(subtract(vertices[b],center),u)));
    found.set(key,indices);
  }
  return [...found.values()];
}

/** Five regular convex polyhedra, normalized to circumradius 1. */
export function platonicSolidData(name = 'icosahedron') {
  if (!PLATONIC_NAMES.includes(name)) throw new RangeError('Unknown Platonic solid');
  const raw = rawVertices(name), radius = norm(raw[0]);
  const vertices = raw.map(p=>p.map(v=>v/radius));
  const distances = [];
  for (let i=0;i<vertices.length;i++) for (let j=i+1;j<vertices.length;j++) distances.push([i,j,distance(vertices[i],vertices[j])]);
  const edgeLength = Math.min(...distances.map(x=>x[2]));
  const edges = distances.filter(x=>Math.abs(x[2]-edgeLength)<EPS).map(([a,b])=>[a,b]);
  const faces = convexFaces(vertices);
  const counts = { vertices: vertices.length, edges: edges.length, faces: faces.length };
  return { name, vertices, edges, faces, edgeLength, circumradius: 1, counts, euler: counts.vertices-counts.edges+counts.faces };
}

/** Orthographic projection; all edges remain visible as a wireframe. */
export function platonicSolidSVG(name = 'icosahedron', options = {}) {
  const data=platonicSolidData(name);
  const yaw=bounded(options.yaw,0.55,-100,100,'yaw'), pitch=bounded(options.pitch,0.38,-100,100,'pitch');
  const size=bounded(options.size,400,160,1600,'size');
  const projected = data.vertices.map(([x,y,z])=>{
    const x1=x*Math.cos(yaw)+z*Math.sin(yaw), z1=-x*Math.sin(yaw)+z*Math.cos(yaw);
    return [size/2+x1*size*.33,size*.45-(y*Math.cos(pitch)-z1*Math.sin(pitch))*size*.33,y*Math.sin(pitch)+z1*Math.cos(pitch)];
  });
  const edges=data.edges.slice().sort((a,b)=>(projected[a[0]][2]+projected[a[1]][2])-(projected[b[0]][2]+projected[b[1]][2]));
  let body=edges.map(([a,b])=>line(projected[a],projected[b],(projected[a][2]+projected[b][2])>0 ? COLORS.cyan : COLORS.blue,1.6)).join('');
  body+=projected.map(p=>circle(p,2.7,COLORS.gold)).join('');
  body+=text(20,size-42,name[0].toUpperCase()+name.slice(1),COLORS.ink,18);
  body+=text(20,size-20,`V ${data.counts.vertices} · E ${data.counts.edges} · F ${data.counts.faces} · V − E + F = ${data.euler}`);
  return frame(size,size,'Platonic solid: '+name,'Exact regular-solid coordinates, orthographic wireframe; all edges shown.',body);
}

/** Vogel-style equal-area spiral placement, an idealized phyllotaxis model. */
export function phyllotaxisData(options = {}) {
  const count=bounded(options.count,233,1,2000,'count',true);
  const divergence=bounded(options.divergence,GOLDEN_ANGLE,0,2*Math.PI,'divergence');
  const radius=bounded(options.radius,1,.001,1000,'radius');
  const points=Array.from({length:count},(_,i)=>{
    const r=radius*Math.sqrt((i+.5)/count), theta=i*divergence;
    return { index:i, r, theta, x:r*Math.cos(theta), y:r*Math.sin(theta) };
  });
  return {count,divergence,divergenceDegrees:divergence*180/Math.PI,radius,points,model:'Equal-area disk samples; not a biological growth simulation'};
}

export function phyllotaxisSVG(options = {}) {
  const data=phyllotaxisData(options), size=bounded(options.size,400,160,1600,'size');
  const scale=size*.37/data.radius, r=Math.max(.8,size*.28/Math.sqrt(data.count));
  const body=data.points.map((p,i)=>circle([size/2+p.x*scale,size*.44-p.y*scale],r,i%13===0 ? COLORS.cyan : COLORS.gold)).join('')+
    text(20,size-42,'Phyllotaxis',COLORS.ink,18)+
    text(20,size-20,`${data.count} points · divergence ${fmt(data.divergenceDegrees)}°`);
  return frame(size,size,'Phyllotaxis spiral','Idealized equal-area spiral points. Radial distance is proportional to the square root of point index.',body);
}

/**
 * Frictionless point mass, start from rest, uniform gravity, y positive DOWN.
 * Solve x/y=(theta-sin(theta))/(1-cos(theta)), theta in (0, 2 pi).
 * Supported endpoint ratios [0.02, 20] avoid degenerate vertical/cusp limits.
 */
export function brachistochroneData(options = {}) {
  const x=bounded(options.x,1,.001,1000,'x'), y=bounded(options.y,1,.001,1000,'y');
  const g=bounded(options.g,9.81,.001,1000,'g'), samples=bounded(options.samples,160,8,2000,'samples',true);
  const ratio=x/y;
  if (ratio < .02 || ratio > 20) throw new RangeError('x/y must be in [0.02, 20]');
  let lo=1e-7, hi=2*Math.PI-1e-7;
  for(let i=0;i<80;i++) { const mid=(lo+hi)/2; if((mid-Math.sin(mid))/(1-Math.cos(mid))<ratio)lo=mid;else hi=mid; }
  const theta=(lo+hi)/2, a=y/(1-Math.cos(theta));
  const cycloidPoint=u=>({x:a*(u-Math.sin(u)),y:a*(1-Math.cos(u))});
  const cycloidTime=theta*Math.sqrt(a/g), straightTime=Math.sqrt(2*(x*x+y*y)/(g*y));
  const points=Array.from({length:samples+1},(_,i)=>cycloidPoint(theta*i/samples));
  // theta increases linearly with elapsed time because ds/v=sqrt(a/g)dtheta.
  const motionAtTime = seconds => {
    const t=bounded(seconds,0,0,1e8,'seconds');
    const tc=Math.min(t,cycloidTime), ts=Math.min(t,straightTime);
    const fraction=(ts/straightTime)**2;
    return {cycloid:cycloidPoint(tc*Math.sqrt(g/a)),straight:{x:x*fraction,y:y*fraction},cycloidFinished:t>=cycloidTime,straightFinished:t>=straightTime};
  };
  return {x,y,g,theta,a,points,cycloidTime,straightTime,timeSavedFraction:1-cycloidTime/straightTime,maxDepth:theta>=Math.PI ? 2*a : y,motionAtTime,assumptions:'Point mass; rest start; uniform gravity; no friction or rolling inertia; y positive down'};
}

export function brachistochroneSVG(options = {}) {
  const d=brachistochroneData(options), width=bounded(options.width,640,320,1600,'width'), height=bounded(options.height,420,280,1200,'height');
  // One scale for both axes: geometry is not distorted to fit the viewport.
  const scale=Math.min((width-100)/d.x,(height-155)/d.maxDepth);
  const left=(width-d.x*scale)/2;
  const p=({x,y})=>[left+x*scale,45+y*scale];
  const path=d.points.map((v,i)=>`${i?'L':'M'}${p(v).map(fmt).join(',')}`).join(' ');
  let body=line(p({x:0,y:0}),p(d),COLORS.gold,2.2,'stroke-dasharray="7 5"')+
    `<path d="${path}" fill="none" stroke="${COLORS.cyan}" stroke-width="3"/>`+
    circle(p({x:0,y:0}),5,COLORS.ink)+circle(p(d),5,COLORS.ink)+text(left-20,25,'Start from rest',COLORS.ink)+
    text(p(d)[0]-35,p(d)[1]+24,'Same endpoint',COLORS.ink);
  if(options.time!==undefined) {
    const t=bounded(options.time,0,0,1e8,'time'), state=d.motionAtTime(t);
    body+=circle(p(state.straight),6,COLORS.gold)+circle(p(state.cycloid),6,COLORS.cyan);
  }
  body+=text(25,height-80,`Cycloid ${d.cycloidTime.toFixed(3)} s`,COLORS.cyan,17)+
    text(25,height-54,`Straight incline ${d.straightTime.toFixed(3)} s`,COLORS.gold,17)+
    text(25,height-28,`x = ${fmt(d.x)} m · drop = ${fmt(d.y)} m · g = ${fmt(d.g)} m/s²`)+
    text(25,height-10,'Ideal point mass · no friction · no rolling inertia',COLORS.muted,10);
  return frame(width,height,'Brachistochrone: cycloid and straight incline','Same start and endpoint under uniform gravity. Cyan cycloid and gold straight incline. Coordinates use a common scale.',body);
}

/**
 * Algebra demonstration only: each junction obeys r0^3=r1^3+r2^3.
 * split allocates the cubic budget, not the cross-sectional area.
 * Angles and segment lengths are illustrative and are not optimized.
 */
export function murrayBranchingData(options = {}) {
  const radius=bounded(options.parentRadius,1,.01,100,'parentRadius');
  const split=bounded(options.split,.5,.1,.9,'split');
  const levels=bounded(options.levels,4,1,7,'levels',true);
  const angle=bounded(options.angle,.48,.15,.8,'angle');
  const segments=[],junctions=[];
  const visit=(start,heading,r,depth,parentIndex)=>{
    const length=.9*.69**depth;
    const end=[start[0]+length*Math.cos(heading),start[1]+length*Math.sin(heading)];
    const index=segments.length; segments.push({start,end,radius:r,depth,parentIndex});
    if(depth<levels) {
      const r1=r*Math.cbrt(split),r2=r*Math.cbrt(1-split);
      junctions.push({parentIndex:index,parentRadius:r,childRadii:[r1,r2],cubicResidual:r**3-r1**3-r2**3});
      visit(end,heading-angle,r1,depth+1,index);
      visit(end,heading+angle,r2,depth+1,index);
    }
  };
  visit([0,0],-Math.PI/2,radius,0,null);
  return {parentRadius:radius,split,levels,angle,segments,junctions,model:'Cubic-radius algebra only; schematic lengths and angles; not a vascular or flow simulation'};
}

export function murrayBranchingSVG(options = {}) {
  const d=murrayBranchingData(options), width=bounded(options.width,600,320,1600,'width'),height=bounded(options.height,440,280,1200,'height');
  const points=d.segments.flatMap(s=>[s.start,s.end]);
  const minX=Math.min(...points.map(p=>p[0])),maxX=Math.max(...points.map(p=>p[0])),minY=Math.min(...points.map(p=>p[1]));
  const scale=Math.min((width-70)/(maxX-minX),(height-120)/(-minY));
  const p=([x,y])=>[width/2+(x-(minX+maxX)/2)*scale,35+(y-minY)*scale];
  let body=d.segments.map(s=>line(p(s.start),p(s.end),s.depth%2 ? COLORS.cyan : COLORS.gold,18*s.radius/d.parentRadius,'stroke-linecap="round"')).join('');
  body+=text(25,height-62,'Murray’s cubic-radius relation',COLORS.ink,18)+
    text(25,height-38,`r₀³ = r₁³ + r₂³ · split ${Math.round(100*d.split)}:${Math.round(100*(1-d.split))}`)+
    text(25,height-15,'Algebra demonstrator; branch angles and lengths are schematic.',COLORS.muted,11);
  return frame(width,height,'Murray law algebra demonstrator','Schematic branching obeys the sum of cubed child radii. This does not predict real vessels, flow, or optimal branching angles.',body);
}
