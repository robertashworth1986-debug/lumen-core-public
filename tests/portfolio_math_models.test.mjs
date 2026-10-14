import test from 'node:test';
import assert from 'node:assert/strict';
import {PLATONIC_NAMES,GOLDEN_ANGLE,platonicSolidData,platonicSolidSVG,phyllotaxisData,phyllotaxisSVG,brachistochroneData,brachistochroneSVG,murrayBranchingData,murrayBranchingSVG} from '../dashboard/portfolio/math-models.mjs';
const near=(a,b,tol=1e-9)=>assert.ok(Math.abs(a-b)<=tol,`${a} is not within ${tol} of ${b}`);
const norm=a=>Math.hypot(...a);
const distance=(a,b)=>norm(a.map((v,i)=>v-b[i]));
const expected={tetrahedron:[4,6,4,3,3],cube:[8,12,6,4,3],octahedron:[6,12,8,3,4],dodecahedron:[20,30,12,5,3],icosahedron:[12,30,20,3,5]};
for(const name of PLATONIC_NAMES) test(`${name}: actual geometry, faces, incidence and Euler`,()=>{
  const s=platonicSolidData(name), [V,E,F,faceDegree,vertexDegree]=expected[name];
  assert.deepEqual(s.counts,{vertices:V,edges:E,faces:F}); assert.equal(s.euler,2);
  assert.equal(new Set(s.vertices.map(v=>v.join(','))).size,V);
  s.vertices.forEach(v=>near(norm(v),1));
  s.edges.forEach(([a,b])=>near(distance(s.vertices[a],s.vertices[b]),s.edgeLength));
  const edgeSet=new Set(s.edges.map(([a,b])=>[a,b].sort((x,y)=>x-y).join(','))), use=new Map();
  const degrees=Array(V).fill(0);s.edges.forEach(([a,b])=>{degrees[a]++;degrees[b]++;});
  degrees.forEach(d=>assert.equal(d,vertexDegree));
  for(const face of s.faces) {
    assert.equal(face.length,faceDegree);
    const center=[0,1,2].map(axis=>face.reduce((sum,i)=>sum+s.vertices[i][axis],0)/face.length);
    const faceRadius=distance(center,s.vertices[face[0]]);
    face.forEach(i=>near(distance(center,s.vertices[i]),faceRadius));
    for(let i=0;i<face.length;i++) {
      const key=[face[i],face[(i+1)%face.length]].sort((a,b)=>a-b).join(',');
      assert.ok(edgeSet.has(key));use.set(key,(use.get(key)||0)+1);
    }
  }
  assert.equal(use.size,E);for(const n of use.values())assert.equal(n,2);
});
test('phyllotaxis: equal annular area increments and golden-angle spacing',()=>{
  const d=phyllotaxisData({count:233});near(d.divergenceDegrees,137.50776405003785);
  for(const [i,p] of d.points.entries()) {
    near(p.x*p.x+p.y*p.y,(i+.5)/233);near(p.theta,i*GOLDEN_ANGLE);
    assert.ok(p.r<1);if(i)near(p.r*p.r-d.points[i-1].r**2,1/233);
  }
});
test('brachistochrone: endpoints, analytic times, independent numerical ds/v integration',()=>{
  for(const [x,y] of [[1,1],[2,1],[.02,1],[20,1]]) {
    const d=brachistochroneData({x,y}),end=d.points.at(-1);near(end.x,x,1e-8);near(end.y,y,1e-8);
    near(d.points[0].x,0);near(d.points[0].y,0);assert.ok(d.cycloidTime<d.straightTime);
    // Midpoint quadrature of ds / sqrt(2 g y); no analytic time formula inside integral.
    const n=10000,dt=d.theta/n;let numeric=0;
    for(let i=0;i<n;i++){
      const t=(i+.5)*dt,dx=d.a*(1-Math.cos(t)),dy=d.a*Math.sin(t),depth=2*d.a*Math.sin(t/2)**2;
      numeric+=Math.hypot(dx,dy)/Math.sqrt(2*d.g*depth)*dt;
    }
    near(numeric,d.cycloidTime,1e-8);
    // Straight path parameter u=z² removes the rest-start endpoint singularity.
    let straight=0;for(let i=0;i<n;i++){const z=(i+.5)/n;straight+=2*z*Math.hypot(x,y)/Math.sqrt(2*d.g*y*z*z)/n;}
    near(straight,d.straightTime,1e-8);
    const before=d.motionAtTime(0),finished=d.motionAtTime(d.straightTime+1);
    near(before.cycloid.x,0);near(before.straight.y,0);near(finished.cycloid.x,x,1e-8);near(finished.straight.y,y);
    const halfway=d.motionAtTime(d.straightTime/2);near(halfway.straight.x,x/4);
  }
  const unit=brachistochroneData();near(unit.theta,2.4120111439135252,1e-9);near(unit.cycloidTime,.5828954631553586,1e-8);
});
test('Murray demonstration: cubic conservation at every junction and terminal sum',()=>{
  for(const split of [.1,.5,.9]) {
    const d=murrayBranchingData({parentRadius:2.3,split,levels:5});assert.equal(d.segments.length,63);assert.equal(d.junctions.length,31);
    d.junctions.forEach(j=>near(j.parentRadius**3,j.childRadii.reduce((sum,r)=>sum+r**3,0),1e-10));
    near(d.segments.filter(s=>s.depth===5).reduce((sum,s)=>sum+s.radius**3,0),2.3**3,1e-10);
  }
});
test('bounded input and SVG safety',()=>{
  for(const f of [()=>platonicSolidSVG('<script>'),()=>phyllotaxisSVG({count:Infinity}),()=>phyllotaxisSVG({divergence:'<svg>'}),()=>brachistochroneData({y:0}),()=>brachistochroneData({x:100,y:1}),()=>murrayBranchingData({levels:50}),()=>platonicSolidSVG('cube',{yaw:NaN})])assert.throws(f,RangeError);
  for(const svg of [platonicSolidSVG(),phyllotaxisSVG(),brachistochroneSVG({time:.3}),murrayBranchingSVG()]){
    assert.ok(svg.startsWith('<svg'));assert.ok(svg.endsWith('</svg>'));assert.ok(svg.includes('<title>'));assert.ok(svg.includes('<desc>'));
    assert.ok(!/NaN|Infinity|undefined|<script|onload=|foreignObject/i.test(svg));
  }
});
