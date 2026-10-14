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

def allocation_model(points, edges):
    """Fixed ideal-DC model. Material fractions follow returned canonical edges."""
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] not in (2, 3) or len(p) < 2 or not np.isfinite(p).all():
        raise ValueError('finite 2D or 3D points required')
    edges = canonical_edges(edges)
    n = len(p)
    if any(a < 0 or b >= n or a == b for a, b in edges) or len(components(n, edges)) != 1:
        raise ValueError('valid connected graph required')
    d = distances(p)
    if np.min(d[np.triu_indices(n, 1)]) <= 1e-12:
        raise ValueError('distinct coordinates required')
    lengths = np.array([d[edge] for edge in edges])
    return dict(n=n, edges=edges, lengths=lengths, uniform_fractions=lengths/lengths.sum())


def conductance_objective(model, fractions, pairs, *, gradient=True):
    """Mean pair conductance and exact circuit sensitivity to material fractions.

    Volume and resistivity are one. g_e = q_e / length_e**2. For unit-current
    pair voltage v, d(1/R)/dq_e = (v_a-v_b)**2/(length_e**2 * R**2).
    """
    q = np.asarray(fractions, dtype=float)
    pairs = np.asarray(pairs)
    n, edges, lengths = model['n'], model['edges'], model['lengths']
    if q.shape != lengths.shape or not np.isfinite(q).all() or np.any(q <= 0) or abs(float(q.sum())-1) > 1e-10:
        raise ValueError('positive finite material fractions must sum to one')
    if pairs.ndim != 2 or pairs.shape[1] != 2 or len(pairs) == 0 or pairs.dtype.kind not in 'iu':
        raise ValueError('nonempty integer terminal pairs required')
    if np.any(pairs < 0) or np.any(pairs >= n) or np.any(pairs[:, 0] == pairs[:, 1]):
        raise ValueError('invalid terminal pair')
    if len({tuple(sorted(pair)) for pair in pairs.tolist()}) != len(pairs):
        raise ValueError('duplicate terminal pair')
    lap = np.zeros((n, n))
    for (a, b), weight in zip(edges, q/lengths**2):
        lap[a, a] += weight; lap[b, b] += weight
        lap[a, b] -= weight; lap[b, a] -= weight
    values, vectors = np.linalg.eigh(lap)
    if values[1] <= values[-1]*1e-12:
        raise ValueError('ill-conditioned allocation')
    inverse = (vectors[:, 1:]/values[1:])@vectors[:, 1:].T
    residual = float(np.max(np.abs(lap@inverse-(np.eye(n)-np.ones((n,n))/n))))
    if residual > 1e-8:
        raise ValueError('allocation conservation residual exceeds tolerance')
    source, sink = pairs.T
    resistance = inverse[source, source]+inverse[sink, sink]-2*inverse[source, sink]
    if np.any(resistance <= 0) or not np.isfinite(resistance).all():
        raise ValueError('invalid pair resistance')
    score = float(np.mean(1/resistance))
    derivatives = None
    if gradient:
        ends = np.array(edges)
        drops = inverse[ends[:, 0]][:, source]-inverse[ends[:, 1]][:, source]-inverse[ends[:, 0]][:, sink]+inverse[ends[:, 1]][:, sink]
        derivatives = np.mean((drops/resistance)**2, axis=1)/lengths**2
        if not np.isfinite(derivatives).all():
            raise ValueError('invalid objective gradient')
    return score, derivatives, residual


def project_material_simplex(values, lower):
    """Euclidean projection onto q >= lower and sum(q) = 1."""
    values, lower = np.asarray(values, dtype=float), np.asarray(lower, dtype=float)
    if values.ndim != 1 or values.shape != lower.shape or not len(values) or not np.isfinite(values).all() or not np.isfinite(lower).all() or np.any(lower < 0):
        raise ValueError('finite vectors with nonnegative material floor required')
    remaining = 1-float(lower.sum())
    if remaining <= 0:
        raise ValueError('material floor must leave positive allocation capacity')
    ordered = np.sort(values-lower)[::-1]
    cumulative = np.cumsum(ordered)
    count = np.arange(1, len(values)+1)
    active = np.flatnonzero(ordered-(cumulative-remaining)/count > 0)[-1]
    threshold = (cumulative[active]-remaining)/(active+1)
    return lower+np.maximum(values-lower-threshold, 0)


def optimize_material(model, training_pairs, protocol):
    """Fit only explicitly supplied training demands; no validation pairs accepted."""
    validate_allocation_protocol(protocol)
    budget = protocol['optimization_budget']
    lower = protocol['physical_constraints']['minimum_cross_section_fraction_of_uniform']*model['uniform_fractions']
    q = model['uniform_fractions'].copy()
    started = time.perf_counter()
    score, grad, residual = conductance_objective(model, q, training_pairs)
    calls = 1; accepted = 0; step = budget['initial_step']; trace = [score]
    termination = 'iteration_budget_exhausted'
    for iteration in range(budget['max_iterations']):
        gap = max(0.0, float((1-lower.sum())*grad.max()-grad@(q-lower)))
        if gap <= budget['relative_dual_gap_tolerance']*max(1.0, abs(score)):
            termination = 'declared_dual_gap_tolerance_reached'; break
        success = False
        for search in range(budget['max_line_search_steps']):
            if calls >= budget['max_solver_calls']:
                termination = 'solver_budget_exhausted'; break
            proposal = project_material_simplex(q+step*grad, lower)
            candidate, candidate_grad, candidate_residual = conductance_objective(model, proposal, training_pairs)
            calls += 1
            residual = max(residual, candidate_residual)
            if candidate >= score+budget['armijo_coefficient']*float(grad@(proposal-q))-1e-13:
                q, score, grad = proposal, candidate, candidate_grad
                accepted += 1; trace.append(score); success = True
                step = min(budget['initial_step'], step*2); break
            step /= 2
        if not success:
            if termination != 'solver_budget_exhausted': termination = 'line_search_exhausted'
            break
    gap = max(0.0, float((1-lower.sum())*grad.max()-grad@(q-lower)))
    if gap <= budget['relative_dual_gap_tolerance']*max(1.0, abs(score)):
        termination = 'declared_dual_gap_tolerance_reached'
    if abs(float(q.sum())-1) > 1e-12 or np.any(q < lower-1e-12):
        raise ValueError('material constraints violated')
    return dict(material_fractions=q.tolist(), training_score=score, training_trace=trace,
                solver_calls=calls, gradient_calls=calls, accepted_steps=accepted,
                elapsed_seconds=time.perf_counter()-started, termination=termination,
                dual_gap_upper_bound=gap, laplacian_identity_max_residual=residual,
                material_volume=float(q.sum()), minimum_area_fraction_of_uniform=float(np.min(q/model['uniform_fractions'])),
                maximum_area_fraction_of_uniform=float(np.max(q/model['uniform_fractions'])))


def validate_allocation_protocol(protocol):
    if protocol.get('schema') != 'lumencore.fixed_volume_dc_allocation_protocol.v1':
        raise ValueError('unknown allocation protocol schema')
    physical = protocol['physical_constraints']
    if any(type(physical[key]) not in (int, float) or not math.isfinite(physical[key]) or physical[key] != 1.0 for key in ('material_volume', 'resistivity', 'diameter')) or type(physical['node_count']) is not int or physical['node_count'] != 64 or physical['topology_and_coordinates_unchanged'] is not True:
        raise ValueError('runner requires declared normalized 64-node fixed geometry')
    floor = physical['minimum_cross_section_fraction_of_uniform']
    if isinstance(floor, bool) or not isinstance(floor, (int, float)) or not math.isfinite(floor) or not 0 < floor < 1:
        raise ValueError('area floor must be finite and strictly between zero and one')
    budget = protocol['optimization_budget']
    for key, maximum in [('max_iterations', 80), ('max_solver_calls', 1000), ('max_line_search_steps', 20)]:
        if type(budget[key]) is not int or not 1 <= budget[key] <= maximum:
            raise ValueError('positive bounded integer search budgets required')
    for key in ('initial_step', 'armijo_coefficient', 'relative_dual_gap_tolerance'):
        if type(budget[key]) not in (int, float) or not math.isfinite(budget[key]) or not 0 < budget[key] <= 1:
            raise ValueError('finite bounded optimization controls required')
    if type(protocol['validation']['fold_count']) is not int or protocol['validation']['fold_count'] != 5 or any(type(seed) is not int or seed < 0 for seed in (protocol['validation']['pair_shuffle_seed'], protocol['random_allocation_seed'])):
        raise ValueError('five folds and integer seeds required')
    if protocol['claim_level'] != 'internal_synthetic_screening_only' or protocol['promotion_gate_passed'] is not False:
        raise ValueError('allocation is an unpromoted internal synthetic screen')


def allocation_pair_folds(protocol):
    all_pairs = np.array([(a, b) for a in range(64) for b in range(a+1, 64)])
    indices = np.random.default_rng(protocol['validation']['pair_shuffle_seed']).permutation(len(all_pairs))
    return all_pairs, np.array_split(indices, protocol['validation']['fold_count'])


def run_allocation(protocol_path):
    protocol_bytes = Path(protocol_path).read_bytes()
    protocol = json.loads(protocol_bytes)
    validate_allocation_protocol(protocol)
    graphs = build_graphs()
    if [graph['id'] for graph in graphs] != protocol['graphs']:
        raise ValueError('frozen graph set mismatch')
    all_pairs, folds = allocation_pair_folds(protocol)
    records = []
    for graph_index, graph in enumerate(graphs):
        model = allocation_model(graph['points'], graph['edges'])
        lower = protocol['physical_constraints']['minimum_cross_section_fraction_of_uniform']*model['uniform_fractions']
        random_q = lower+(1-lower.sum())*np.random.default_rng(protocol['random_allocation_seed']+graph_index).dirichlet(np.ones(len(lower)))
        results = []
        for fold_index, validation_indices in enumerate(folds):
            train_indices = np.concatenate([fold for index, fold in enumerate(folds) if index != fold_index])
            fit = optimize_material(model, all_pairs[train_indices], protocol)
            scores = {}
            for label, q in [('uniform', model['uniform_fractions']), ('random', random_q), ('fitted', fit['material_fractions'])]:
                started = time.perf_counter()
                value, _, residual = conductance_objective(model, q, all_pairs[validation_indices], gradient=False)
                scores[label] = dict(mean_effective_conductance=value, elapsed_seconds=time.perf_counter()-started,
                                     solver_calls=1, laplacian_identity_max_residual=residual)
            delta = scores['fitted']['mean_effective_conductance']-scores['uniform']['mean_effective_conductance']
            results.append(dict(fold=fold_index, training_pair_count=len(train_indices), validation_pair_count=len(validation_indices),
                                fit=fit, validation=scores, held_out_absolute_delta=delta,
                                held_out_relative_delta=delta/scores['uniform']['mean_effective_conductance']))
        deltas = [row['held_out_relative_delta'] for row in results]
        records.append(dict(id=graph['id'], comparison_group=graph['comparison_group'],
                            edge_count=len(graph['edges']), random_material_fractions=random_q.tolist(),
                            folds=results, mean_relative_delta=float(np.mean(deltas)),
                            minimum_relative_delta=min(deltas), maximum_relative_delta=max(deltas),
                            negative_or_zero_folds=sum(value <= 0 for value in deltas),
                            descriptive_all_five_positive=all(value > 0 for value in deltas)))
    return dict(schema='lumencore.fixed_volume_dc_allocation_results.v1', generated_utc=datetime.now(timezone.utc).isoformat(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                protocol_sha256=hashlib.sha256(protocol_bytes).hexdigest(),
                claim_level='internal_synthetic_screening_only', promotion_gate_passed=False,
                python=platform.python_version(), numpy=np.__version__,
                validation_fold_pair_indices=[fold.tolist() for fold in folds],
                pairs=all_pairs.tolist(), graphs=records,
                limitations=protocol['limitations']+[protocol['validation']['scope'], protocol['uncertainty']])


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
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='results.json'); parser.add_argument('--edge-outages',action='store_true',help='also exhaust single-wire conductance stress without material reallocation'); parser.add_argument('--allocation-protocol',type=Path,help='run fixed-volume allocation study using a frozen protocol'); args=parser.parse_args()
    if args.allocation_protocol and args.edge_outages: parser.error('allocation and legacy outage studies are separate')
    output=run_allocation(args.allocation_protocol) if args.allocation_protocol else run(edge_outages=args.edge_outages); output['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    Path(args.output).write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    for g in output['graphs']:
        if args.allocation_protocol:
            print(f"{g['id']:24s} mean held-out delta={100*g['mean_relative_delta']:+.3f}% nonpositive folds={g['negative_or_zero_folds']}/5")
            continue
        m=g['metrics']; print(f"{g['id']:24s} E={m['edge_count']:3d} L={m['total_wire_length']:.4f} C={m['mean_effective_conductance']:.6f} stretch={m['mean_path_stretch']:.4f} robust={m['fraction_deletions_preserving_full_connectivity']:.3f}")
