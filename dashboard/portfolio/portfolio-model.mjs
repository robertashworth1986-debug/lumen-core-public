export function filterFamilies(families,search='',lane='all',stage='all') {
 const q=search.trim().toLocaleLowerCase();return families.filter(f=>(lane==='all'||f.lane===lane)&&(stage==='all'||f.status.includes(stage))&&(!q||[f.label,f.id,f.lane,...(f.aliases||[]),...(f.members||[])].join(' ').toLocaleLowerCase().includes(q)));
}
export function componentsAfterBreak(graph,edgeIndex=null) {
 if(!graph||!Array.isArray(graph.nodes)||!Array.isArray(graph.edges)||graph.nodes.length>10000)throw new TypeError('Invalid graph.');
 if(edgeIndex!==null&&(!Number.isInteger(edgeIndex)||edgeIndex<0||edgeIndex>=graph.edges.length))throw new RangeError('Invalid edge.');
 const adj=graph.nodes.map(()=>[]);graph.edges.forEach(([a,b],i)=>{if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b<0||a>=adj.length||b>=adj.length)throw new RangeError('Invalid node.');if(i!==edgeIndex){adj[a].push(b);adj[b].push(a);}});
 const labels=Array(adj.length).fill(-1),sizes=[];for(let i=0;i<adj.length;i++)if(labels[i]===-1){const component=sizes.length,stack=[i];labels[i]=component;let n=0;while(stack.length){const a=stack.pop();n++;for(const b of adj[a])if(labels[b]===-1){labels[b]=component;stack.push(b);}}sizes.push(n);}return{labels,sizes,connected:sizes.length===1};
}
export const humanize=s=>s.replaceAll('_',' ');
