import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {filterFamilies,componentsAfterBreak} from '../dashboard/portfolio/portfolio-model.mjs';
const base=resolve(dirname(fileURLToPath(import.meta.url)),'../dashboard/portfolio');
const registry=JSON.parse(readFileSync(resolve(base,'data/registry.json')));
const transport=JSON.parse(readFileSync(resolve(base,'data/transport.json')));
test('registry aliases, lanes, stages and empty results are coherent',()=>{
 assert.equal(registry.families.length,26);assert.equal(Object.keys(registry.lanes).length,11);assert.equal(new Set(registry.families.map(f=>f.id)).size,26);
 for(const f of registry.families)assert.ok(registry.lanes[f.lane]);
 assert.ok(filterFamilies(registry.families,'fungus').some(f=>f.id==='mycelium_network'));
 assert.ok(filterFamilies(registry.families,'sunflower').some(f=>f.id==='sunflower_phyllotaxis'));
 assert.ok(filterFamilies(registry.families,'icosahedron').some(f=>f.id==='platonic_solids'));
 assert.equal(filterFamilies(registry.families,'no-such-geometry').length,0);
 assert.ok(filterFamilies(registry.families,'','packing_topology','visualization').every(f=>f.lane==='packing_topology'&&f.status==='visualization_only'));
});
test('interactive break model independently reproduces all saved single-edge connectivity fractions',()=>{
 for(const g of transport.graphs){assert.equal(g.nodes.length,64);assert.ok(componentsAfterBreak(g).connected);let preserved=0,totalPairs=0,worst=1;
 for(let i=0;i<g.edges.length;i++){const c=componentsAfterBreak(g,i);preserved+=Number(c.connected);const fraction=c.sizes.reduce((s,n)=>s+n*(n-1)/2,0)/2016;totalPairs+=fraction;worst=Math.min(worst,fraction);}
 assert.ok(Math.abs(preserved/g.edges.length-g.metrics.fraction_deletions_preserving_full_connectivity)<1e-12,g.id);
 assert.ok(Math.abs(totalPairs/g.edges.length-g.metrics.mean_connected_pair_fraction_after_one_edge_failure)<1e-12,g.id);
 assert.ok(Math.abs(worst-g.metrics.worst_connected_pair_fraction_after_one_edge_failure)<1e-12,g.id);
 }
 assert.throws(()=>componentsAfterBreak(transport.graphs[0],-1));assert.throws(()=>componentsAfterBreak(transport.graphs[0],1.2));
});
test('comparison keeps changed terminal embeddings separate and requires preserved negative outcomes',()=>{
 const controlled=transport.graphs.filter(g=>g.comparison_group==='controlled_same_terminals');assert.equal(controlled.length,6);for(const g of controlled)assert.deepEqual(g.nodes,controlled[0].nodes);
 assert.equal(transport.promotion_gate_passed,false);assert.equal(transport.graphs.find(g=>g.id==='honeycomb').comparison_group,'exploratory_different_terminals');
 const a=transport.graphs.find(g=>g.id==='square_grid').metrics,b=transport.graphs.find(g=>g.id==='triangulated_grid').metrics;assert.ok(a.mean_effective_conductance>b.mean_effective_conductance);assert.ok(a.mean_path_stretch>b.mean_path_stretch);
});
test('public page references shipped assets, valid IDs and safe source routes',()=>{
 const html=readFileSync(resolve(base,'index.html'),'utf8');const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(ids.length,new Set(ids).size);
 for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g)){const url=m[1];if(/^(?:https?:|data:)/.test(url))continue;if(url.startsWith('#')){assert.ok(ids.includes(url.slice(1)),url);continue;}const local=url.split('#')[0];assert.ok(existsSync(resolve(base,local)),url);}
 for(const m of html.matchAll(/<label for="([^"]+)"/g))assert.ok(ids.includes(m[1]));
 const summary=readFileSync(resolve(base,'data/review-status.json'),'utf8');assert.ok(!/@|zoom\.us|EPRI_5265/.test(summary));
});
