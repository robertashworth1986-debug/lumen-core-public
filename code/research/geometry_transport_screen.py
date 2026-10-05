"""Synthetic, dimensionless DC resistor-network screening. Not a signal simulation.
Run: python code/research/geometry_transport_screen.py --output results.json
Dependencies: Python 3.11+, NumPy 2.x. No network or external datasets.
"""
from __future__ import annotations
import argparse, hashlib, json, math, platform, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

SEED = 20261005
SCHEMA = 'lumencore.synthetic_resistor_screen.v1'

def distances(points):
    p=np.asarray(points,dtype=float)
    return np.linalg.norm(p[:,None,:]-p[None,:,:],axis=2)

def normalize(points):
    p=np.asarray(points,dtype=float)
    p-=p.mean(axis=0)
    return p/float(distances(p).max())

def canonical_edges(edges):
    result=set()
    for edge in edges:
        if len(edge)!=2 or any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,np.integer)) for v in edge):
            raise ValueError('edges require exactly two integer node indices')
        result.add(tuple(sorted(map(int,edge))))
    return sorted(result)

def components(n, edges):
    neighbors=[[] for _ in range(n)]
    for a,b in edges: neighbors[a].append(b); neighbors[b].append(a)
    visited=set(); parts=[]
    for node in range(n):
        if node in visited: continue
        group=[]; queue=[node]; visited.add(node)
        while queue:
            u=queue.pop(); group.append(u)
            for v in neighbors[u]:
                if v not in visited: visited.add(v); queue.append(v)
        parts.append(group)
    return parts

def mst(points, candidate_edges=None, randomized=False, seed=SEED):
    n=len(points); d=distances(points)
    edges=canonical_edges(candidate_edges if candidate_edges is not None else [(i,j) for i in range(n) for j in range(i+1,n)])
    rng=np.random.default_rng(seed)
    # Randomized Kruskal is a null control, not a uniformly sampled spanning tree.
    order=sorted(edges,key=(lambda e: float(rng.random())) if randomized else lambda e:(round(float(d[e]),12),e))
    parent=list(range(n))
    def root(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    result=[]
    for a,b in order:
        ra,rb=root(a),root(b)
        if ra!=rb: parent[ra]=rb; result.append((a,b))
    if len(result)!=n-1: raise ValueError('candidate graph disconnected')
    return canonical_edges(result)

def shortest_distances(points,edges):
    n=len(points); d=distances(points); s=np.full((n,n),np.inf); np.fill_diagonal(s,0)
    for a,b in edges: s[a,b]=s[b,a]=d[a,b]
    for k in range(n): s=np.minimum(s,s[:,k,None]+s[None,k,:])
    return s

def loop_augment(points, tree, candidates, target_edges=96):
    """Greedy largest detour/edge-length closure; not a biological growth model."""
    edges=set(tree); d=distances(points)
    while len(edges)<target_edges:
        paths=shortest_distances(points,edges)
        available=[e for e in candidates if e not in edges]
        if not available: break
        winner=min(available,key=lambda e:(-round(float(paths[e]/d[e]),12),round(float(d[e]),12),e))
        edges.add(winner)
    return canonical_edges(edges)

def build_graphs(seed=SEED):
    p=normalize([(c,r) for r in range(8) for c in range(8)])
    square=[]; tri=[]
    for r in range(8):
        for c in range(8):
            i=r*8+c
            if c<7: square.append((i,i+1))
            if r<7: square.append((i,i+8))
            if c<7 and r<7: tri.append((i,i+9))
    square=canonical_edges(square); tri=canonical_edges(square+tri)
    serpent=[r*8+c for r in range(8) for c in (range(8) if r%2==0 else range(7,-1,-1))]
    chain=canonical_edges(zip(serpent,serpent[1:])); tree=mst(p)
    defs=[
      ('serpentine_chain','Serpentine chain',p,chain,'controlled_same_terminals','plain connected path; Hamiltonian serpentine path through grid'),
      ('square_grid','Square grid',p,square,'controlled_same_terminals','nearest horizontal and vertical neighbors'),
      ('triangulated_grid','Triangulated square grid',p,tri,'controlled_same_terminals','square grid plus one fixed diagonal per cell; not equilateral triangular lattice'),
      ('minimum_spanning_tree','Minimum spanning tree',p,tree,'controlled_same_terminals','Euclidean MST; deterministic lexicographic tie break'),
      ('loop_augmented_tree','Loop-augmented tree',p,loop_augment(p,tree,tri),'controlled_same_terminals','MST plus greedy detour closures to 96 edges; mycelium-inspired analogy only'),
      ('randomized_tree','Randomized tree control',p,mst(p,tri,True,seed),'controlled_same_terminals','randomized Kruskal on triangulated grid; not uniform over spanning trees'),
    ]
    # Honeycomb: 8 by 4 unit cells, two sublattices; open boundary.
    h=np.array([(math.sqrt(3)*(i+j/2),1.5*j+b) for j in range(4) for i in range(8) for b in (0,1)])
    hd=distances(h); he=[(i,j) for i in range(64) for j in range(i+1,64) if abs(hd[i,j]-1)<1e-9]
    defs.append(('honeycomb','Honeycomb patch',normalize(h),he,'exploratory_different_terminals','64 vertices of honeycomb lattice, 8×4 cells, open boundary'))
    angle=math.pi*(3-math.sqrt(5)); sp=np.array([(math.sqrt((i+.5)/64)*math.cos(i*angle),math.sqrt((i+.5)/64)*math.sin(i*angle)) for i in range(64)])
    sd=distances(sp); se=[]
    for i in range(64):
        se.extend((i,int(j)) for j in np.argsort(sd[i],kind='stable')[1:4])
    se=canonical_edges(se+mst(sp))
    defs.append(('sunflower_knn','Sunflower 3-neighbor network',normalize(sp),se,'exploratory_different_terminals','Vogel golden-angle points; symmetrized 3-nearest-neighbor graph plus MST connectivity safety net'))
    return [dict(id=k,label=l,points=pts,edges=canonical_edges(e),comparison_group=g,construction=c,seed=seed if k=='randomized_tree' else None) for k,l,pts,e,g,c in defs]

def resistor_analysis(points,edges,volume=1.0,resistivity=1.0):
    p=np.asarray(points,dtype=float); n=len(p); edges=canonical_edges(edges)
    if p.ndim!=2 or p.shape[1] not in (2,3) or n<2 or not np.isfinite(p).all(): raise ValueError('finite 2D or 3D points required')
    if not math.isfinite(volume) or volume<=0 or not math.isfinite(resistivity) or resistivity<=0: raise ValueError('positive finite budget and resistivity required')
    if any(a<0 or b>=n or a==b for a,b in edges): raise ValueError('invalid edge')
    if len(components(n,edges))!=1: raise ValueError('connected graph required')
    euclidean=distances(p)
    if np.min(euclidean[np.triu_indices(n,1)])<=1e-12: raise ValueError('distinct coordinates required for all node pairs')
    lengths=np.array([euclidean[e] for e in edges])
    if np.any(lengths<=1e-12): raise ValueError('coincident edge endpoints')
    total=float(lengths.sum()); area=volume/total; weights=area/(resistivity*lengths)
    lap=np.zeros((n,n))
    for (a,b),g in zip(edges,weights): lap[a,a]+=g; lap[b,b]+=g; lap[a,b]-=g; lap[b,a]-=g
    values,vectors=np.linalg.eigh(lap)
    if values[1]<=values[-1]*1e-12: raise ValueError('ill-conditioned graph')
    pseudoinverse=(vectors[:,1:]/values[1:])@vectors[:,1:].T
    resistance=np.diag(pseudoinverse)[:,None]+np.diag(pseudoinverse)[None,:]-2*pseudoinverse
    pair=np.triu_indices(n,1); r=resistance[pair]
    if np.min(r)<=0: raise ValueError('nonpositive pair resistance')
    paths=shortest_distances(p,edges); stretch=paths[pair]/euclidean[pair]
    residual=float(np.max(np.abs(lap@pseudoinverse-(np.eye(n)-np.ones((n,n))/n))))
    metrics=dict(node_count=n,edge_count=len(edges),terminal_pair_count=n*(n-1)//2,diameter=float(euclidean.max()),total_wire_length=total,uniform_cross_section=area,material_budget=float(area*lengths.sum()),mean_effective_conductance=float(np.mean(1/r)),mean_effective_resistance=float(np.mean(r)),mean_path_stretch=float(stretch.mean()),worst_path_stretch=float(stretch.max()),laplacian_identity_max_residual=residual)
    return metrics,lap,resistance,weights

def failure_analysis(n,edges):
    fractions=[]; full=[]; worst_edge=None; worst=2.0
    for i,edge in enumerate(edges):
        groups=components(n,edges[:i]+edges[i+1:])
        fraction=sum(len(g)*(len(g)-1) for g in groups)/(n*(n-1))
        fractions.append(fraction); full.append(len(groups)==1)
        if fraction<worst: worst=fraction; worst_edge=edge
    return dict(single_edge_failures_tested=len(edges),fraction_deletions_preserving_full_connectivity=float(np.mean(full)),mean_connected_pair_fraction_after_one_edge_failure=float(np.mean(fractions)),worst_connected_pair_fraction_after_one_edge_failure=float(min(fractions)),worst_deleted_edge=list(worst_edge))

def outage_conductance_analysis(points, edges, volume=1.0, resistivity=1.0):
    """Exhaust every single-wire outage without redistributing surviving material.

    A connected deletion uses the rank-one Laplacian inverse update. A bridge
    deletion leaves within-component resistances unchanged and disconnects every
    cross-component pair. The original all-pairs denominator is always retained.
    These are secondary stress metrics, not a replacement primary objective.
    """
    edges = canonical_edges(edges)
    baseline, _, resistance, weights = resistor_analysis(points, edges, volume, resistivity)
    n = baseline['node_count']
    pairs = np.triu_indices(n, 1)
    baseline_conductance = 1.0 / resistance[pairs]
    records = []
    max_monotonicity_residual = 0.0
    for index, (a, b) in enumerate(edges):
        groups = components(n, edges[:index] + edges[index + 1:])
        if len(groups) == 1:
            # q_i - q_j from L+ (e_a - e_b), recovered from pair resistance.
            q = (resistance[:, b] - resistance[:, a]) / 2.0
            denominator = 1.0 - weights[index] * resistance[a, b]
            if not math.isfinite(denominator) or denominator <= 1e-12:
                raise ValueError('ill-conditioned connected outage update')
            updated = resistance[pairs] + weights[index] * (q[pairs[0]] - q[pairs[1]]) ** 2 / denominator
            conductance = 1.0 / updated
            method = 'connected_rank_one_update'
        else:
            labels = np.empty(n, dtype=int)
            for label, group in enumerate(groups):
                labels[group] = label
            conductance = np.where(labels[pairs[0]] == labels[pairs[1]], baseline_conductance, 0.0)
            method = 'bridge_component_identity'
        if not np.isfinite(conductance).all() or np.any(conductance < 0):
            raise ValueError('invalid post-outage conductance')
        residual = float(np.max(conductance - baseline_conductance))
        max_monotonicity_residual = max(max_monotonicity_residual, residual)
        if residual > 1e-10 * max(1.0, float(baseline_conductance.max())):
            raise ValueError('edge deletion increased conductance')
        mean = float(np.mean(conductance))
        records.append({
            'deleted_edge': [a, b],
            'method': method,
            'connected_pair_fraction': sum(len(g) * (len(g) - 1) for g in groups) / (n * (n - 1)),
            'mean_effective_conductance': mean,
            'conductance_retention_fraction': mean / baseline['mean_effective_conductance'],
        })
    worst = min(records, key=lambda row: (row['mean_effective_conductance'], row['deleted_edge']))
    return {
        'material_policy': 'surviving wire cross-sections and resistivity unchanged; deleted material is lost',
        'terminal_pair_policy': 'all original unordered pairs; disconnected pairs have zero conductance',
        'outage_aggregation': 'equal weight per edge deletion; descriptive exhaustive stress, not a probability or confidence interval',
        'single_edge_failures_tested': len(records),
        'connected_deletions': sum(row['method'] == 'connected_rank_one_update' for row in records),
        'disconnecting_deletions': sum(row['method'] == 'bridge_component_identity' for row in records),
        'baseline_mean_effective_conductance': baseline['mean_effective_conductance'],
        'mean_effective_conductance_after_one_edge_failure': float(np.mean([row['mean_effective_conductance'] for row in records])),
        'mean_conductance_retention_fraction': float(np.mean([row['conductance_retention_fraction'] for row in records])),
        'worst_effective_conductance_after_one_edge_failure': worst['mean_effective_conductance'],
        'worst_conductance_retention_fraction': worst['conductance_retention_fraction'],
        'worst_deleted_edge': worst['deleted_edge'],
        'max_positive_rayleigh_monotonicity_residual': max_monotonicity_residual,
        'deletions': records,
    }

def run(*, edge_outages=False):
    generated = datetime.now(timezone.utc)
    records=[]; start=time.perf_counter()
    for graph in build_graphs():
        metrics,lap,r,w=resistor_analysis(graph['points'],graph['edges'])
        metrics.update(failure_analysis(len(graph['points']),graph['edges']))
        record={k:v for k,v in graph.items() if k not in ('points','edges')}
        record.update(nodes=graph['points'].tolist(),edges=[list(e) for e in graph['edges']],metrics=metrics)
        if edge_outages:
            record['outage_conductance'] = outage_conductance_analysis(graph['points'], graph['edges'])
        records.append(record)
    return dict(schema=SCHEMA,claim_level='internal_synthetic_screening_only',promotion_gate_passed=False,run_date=generated.date().isoformat(),generated_utc=generated.isoformat(),edge_outages_requested=edge_outages,purpose='Compare ideal DC resistor-network transport and topological fault tolerance under declared normalized constraints.',primary_metric='mean_effective_conductance (higher within the controlled group only; all 2016 terminal pairs equally weighted)',reference_baseline='square_grid',normalization=dict(node_count=64,diameter=1,material_budget=1,resistivity=1,uniform_cross_section_per_graph=True,terminal_pairs='all unordered pairs, equal weights',boundary='open boundaries, pairwise source and sink; all other nodes obey Kirchhoff current conservation'),seeds=dict(randomized_tree=SEED,all_other_graphs='deterministic, no random numbers'),metric_units=dict(diameter='D',total_wire_length='D',uniform_cross_section='V/D',material_budget='V',mean_effective_conductance='V/(rho*D^2); normalized dimensionless when D=V=rho=1',mean_effective_resistance='rho*D^2/V',mean_path_stretch='dimensionless',worst_path_stretch='dimensionless',failure_metrics='fractions of exhaustive single-edge deletions or node pairs'),limitations=['No time, frequency, capacitance, inductance, dielectric loss, impedance matching, bandwidth, attenuation, signal-to-noise, Maxwell equations, or fluid dynamics are modeled.','Adding wire lowers every edge cross-section at fixed volume; conductance need not improve. Edge count is disclosed, not held fixed.','Honeycomb and sunflower use different terminal coordinates and boundary aspect ratios: exploratory embedding comparison only; do not pool or rank as controlled topology gains.','Only one deterministic layout per family and one fixed random control seed. This is not the frozen multi-fold promotion gate, uncertainty analysis, or experimental validation.','Loop-augmented tree is a designed heuristic, not a validated fungal or slime-mold growth model.','Wire intersections away from named nodes do not create junctions; edge overlaps, finite conductor width, contact resistance, junction volume, and manufacturability are ignored.','The original fault metrics measure connectivity only. Optional edge-outage conductance is ideal steady DC with surviving material fixed; no targeted node damage, correlated failures, healing, or physical reliability probabilities are modeled.','Uniform cross-section is a policy choice; no optimal radius allocation, Murray-law hydraulic model, or equal compute budget for topology construction is claimed.','Metric choice and graph definitions were fixed before this run, but there is no independent preregistration or holdout dataset. No family status or legacy finding is promoted.'],solver=dict(method='NumPy symmetric eigendecomposition of weighted graph Laplacian; all-pairs effective resistance from Moore–Penrose inverse',pseudoinverse_zero_mode='discard exactly one known connected-graph zero eigenmode',condition_guard='lambda_2/lambda_max > 1e-12',python=platform.python_version(),numpy=np.__version__,elapsed_seconds=time.perf_counter()-start),graphs=records)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='results.json'); parser.add_argument('--edge-outages',action='store_true',help='also exhaust single-wire conductance stress without material reallocation'); args=parser.parse_args()
    output=run(edge_outages=args.edge_outages); output['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    Path(args.output).write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    for g in output['graphs']:
        m=g['metrics']; print(f"{g['id']:24s} E={m['edge_count']:3d} L={m['total_wire_length']:.4f} C={m['mean_effective_conductance']:.6f} stretch={m['mean_path_stretch']:.4f} robust={m['fraction_deletions_preserving_full_connectivity']:.3f}")
