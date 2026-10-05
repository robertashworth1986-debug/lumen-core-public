import math, unittest
import numpy as np
import importlib.util
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_module_path = Path(__file__).resolve().parents[1] / 'code' / 'research' / 'geometry_transport_screen.py'
_spec = importlib.util.spec_from_file_location('geometry_transport_screen', _module_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
build_graphs = _module.build_graphs
resistor_analysis = _module.resistor_analysis
failure_analysis = _module.failure_analysis
components = _module.components
distances = _module.distances
outage_conductance_analysis = _module.outage_conductance_analysis


def grounded_outage_reference(points, edges, weights, deleted):
    """Independent direct grounded inverses; no update formula or re-budgeting."""
    n = len(points)
    surviving = edges[:deleted] + edges[deleted + 1:]
    laplacian = np.zeros((n, n))
    for index, ((a, b), weight) in enumerate(zip(edges, weights)):
        if index == deleted:
            continue
        laplacian[a, a] += weight
        laplacian[b, b] += weight
        laplacian[a, b] -= weight
        laplacian[b, a] -= weight
    conductance_sum = 0.0
    for group in components(n, surviving):
        if len(group) == 1:
            continue
        keep = group[:-1]
        grounded_inverse = np.linalg.solve(laplacian[np.ix_(keep, keep)], np.eye(len(keep)))
        inverse = np.zeros((len(group), len(group)))
        inverse[:-1, :-1] = grounded_inverse
        resistances = np.diag(inverse)[:, None] + np.diag(inverse)[None, :] - 2 * inverse
        conductance_sum += np.sum(1.0 / resistances[np.triu_indices(len(group), 1)])
    return conductance_sum / (n * (n - 1) / 2)


def benchmark_outage_solvers(repeats=3):
    """Diagnostic timing only; both paths include their unfaulted baseline solve."""
    graphs = build_graphs()
    timings = []
    max_error = 0.0
    for repeat in range(repeats):
        values = {}
        # Alternate ordering to avoid giving one implementation every first pass.
        methods = ('optimized', 'direct') if repeat % 2 == 0 else ('direct', 'optimized')
        timing = {}
        for method in methods:
            started = time.perf_counter()
            scores = []
            for graph in graphs:
                points, edges = graph['points'], graph['edges']
                if method == 'optimized':
                    scores.extend(row['mean_effective_conductance'] for row in outage_conductance_analysis(points, edges)['deletions'])
                else:
                    _, _, _, weights = resistor_analysis(points, edges)
                    scores.extend(grounded_outage_reference(points, edges, weights, index) for index in range(len(edges)))
            timing[f'{method}_seconds'] = time.perf_counter() - started
            values[method] = np.array(scores)
        error = float(np.max(np.abs(values['optimized'] - values['direct'])))
        if error > 1e-9:
            raise AssertionError(f'independent outage solver discrepancy: {error}')
        max_error = max(max_error, error)
        timing['execution_order'] = list(methods)
        timings.append(timing)
    optimized = float(np.median([row['optimized_seconds'] for row in timings]))
    direct = float(np.median([row['direct_seconds'] for row in timings]))
    return {
        'schema': 'lumencore.outage_solver_comparison.v1',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'numpy': np.__version__,
        'graph_count': len(graphs),
        'outage_count_per_pass': sum(len(graph['edges']) for graph in graphs),
        'repetitions': repeats,
        'max_absolute_mean_conductance_error': max_error,
        'timing_passes': timings,
        'median_optimized_seconds': optimized,
        'median_direct_seconds': direct,
        'direct_to_optimized_median_runtime_ratio': direct / optimized,
        'boundary': 'First-party diagnostic on one machine; same finite circuits and baseline cost, graph construction excluded equally. No field or general hardware speed claim.',
    }

class TransportTests(unittest.TestCase):
    def test_series_exact(self):
        m,L,R,w=resistor_analysis([(0,0),(1,0),(2,0)],[(0,1),(1,2)])
        self.assertAlmostEqual(R[0,2],4,places=12)
        self.assertAlmostEqual(R[0,1],2,places=12)
    def test_equal_triangle_exact(self):
        m,L,R,w=resistor_analysis([(0,0),(1,0),(.5,math.sqrt(3)/2)],[(0,1),(1,2),(0,2)])
        self.assertAlmostEqual(m['mean_effective_conductance'],.5,places=12)
    def test_square_parallel_paths_exact(self):
        m,L,R,w=resistor_analysis([(0,0),(1,0),(1,1),(0,1)],[(0,1),(1,2),(2,3),(0,3)])
        self.assertAlmostEqual(R[0,1],3,places=12)
        self.assertAlmostEqual(R[0,2],4,places=12)
    def test_independent_grounded_solve_all_graphs(self):
        for g in build_graphs():
            m,L,R,w=resistor_analysis(g['points'],g['edges'])
            for a,b in [(0,63),(4,36),(23,55)]:
                current=np.zeros(64); current[a]=1; current[b]=-1
                keep=[i for i in range(64) if i!=b]
                voltage=np.zeros(64); voltage[keep]=np.linalg.solve(L[np.ix_(keep,keep)],current[keep])
                self.assertAlmostEqual(voltage[a],R[a,b],places=8)
                self.assertLess(np.max(abs(L@voltage-current)),1e-10)
                dissipation=sum(wi*(voltage[i]-voltage[j])**2 for (i,j),wi in zip(g['edges'],w))
                self.assertAlmostEqual(dissipation,voltage[a],places=8)
    def test_matched_constraints_and_simple_graphs(self):
        graphs=build_graphs(); shared=graphs[0]['points']
        for g in graphs:
            self.assertEqual(len(g['points']),64); self.assertEqual(len(components(64,g['edges'])),1)
            self.assertEqual(len(g['edges']),len(set(g['edges'])))
            m,L,R,w=resistor_analysis(g['points'],g['edges'])
            self.assertAlmostEqual(m['diameter'],1,places=12)
            self.assertAlmostEqual(m['material_budget'],1,places=12)
            self.assertLess(m['laplacian_identity_max_residual'],1e-10)
            self.assertGreaterEqual(m['mean_path_stretch'],1-1e-12)
            if g['comparison_group']=='controlled_same_terminals': np.testing.assert_array_equal(shared,g['points'])
    def test_rigid_motion_and_scale_laws(self):
        g=build_graphs()[4]; p=g['points']; e=g['edges']; m,*_=resistor_analysis(p,e)
        q=p@np.array([[0,-1],[1,0]])+np.array([3,-4]); qm,*_=resistor_analysis(q,e)
        self.assertAlmostEqual(qm['mean_effective_conductance'],m['mean_effective_conductance'],places=11)
        sm,*_=resistor_analysis(p*3,e); vm,*_=resistor_analysis(p,e,volume=7); rm,*_=resistor_analysis(p,e,resistivity=2)
        self.assertAlmostEqual(sm['mean_effective_conductance']*9,m['mean_effective_conductance'],places=11)
        self.assertAlmostEqual(vm['mean_effective_conductance']/7,m['mean_effective_conductance'],places=11)
        self.assertAlmostEqual(rm['mean_effective_conductance']*2,m['mean_effective_conductance'],places=11)
    def test_tree_failure_exact(self):
        m=failure_analysis(3,[(0,1),(1,2)])
        self.assertEqual(m['fraction_deletions_preserving_full_connectivity'],0)
        self.assertAlmostEqual(m['mean_connected_pair_fraction_after_one_edge_failure'],1/3)
    def test_cycle_failure_exact(self):
        m=failure_analysis(4,[(0,1),(1,2),(2,3),(0,3)])
        self.assertEqual(m['fraction_deletions_preserving_full_connectivity'],1)
        self.assertEqual(m['worst_connected_pair_fraction_after_one_edge_failure'],1)
    def test_determinism_and_seed_effect(self):
        a=build_graphs(42); b=build_graphs(42); c=build_graphs(43)
        for x,y in zip(a,b):
            np.testing.assert_array_equal(x['points'],y['points']); self.assertEqual(x['edges'],y['edges'])
        self.assertNotEqual(a[5]['edges'],c[5]['edges'])
        for i in (0,1,2,3,4,6,7): self.assertEqual(a[i]['edges'],c[i]['edges'])
    def test_honeycomb_geometry(self):
        g=build_graphs()[6]; d=distances(g['points']); lengths=[d[e] for e in g['edges']]
        self.assertLess(max(lengths)-min(lengths),1e-12)
        degrees=[sum(i in e for e in g['edges']) for i in range(64)]
        self.assertLessEqual(max(degrees),3)
    def test_negative_inputs_rejected(self):
        cases=[([(0,0),(1,0),(2,0)],[(0,1)]), ([(0,0),(0,0)],[(0,1)]), ([(0,0),(math.nan,0)],[(0,1)])]
        for p,e in cases:
            with self.assertRaises(ValueError): resistor_analysis(p,e)
        with self.assertRaises(ValueError): resistor_analysis([(0,0),(1,0)],[(0,1)],volume=0)
        with self.assertRaises(ValueError): resistor_analysis([(0,0),(1,0)],[(0,1)],resistivity=-1)
        with self.assertRaises(ValueError): resistor_analysis([(0,0),(1,0)],[(0.0,1)])
        with self.assertRaises(ValueError): resistor_analysis([(0,0),(1,0)],[(False,1)])
        with self.assertRaises(ValueError): resistor_analysis([(0,0),(1,0),(0,0)],[(0,1),(1,2)])

    def test_outage_triangle_keeps_surviving_cross_sections(self):
        result = outage_conductance_analysis([(0,0),(1,0),(.5,math.sqrt(3)/2)],[(0,1),(1,2),(0,2)])
        for row in result['deletions']:
            self.assertAlmostEqual(row['mean_effective_conductance'],5/18,places=12)
            self.assertAlmostEqual(row['conductance_retention_fraction'],5/9,places=12)
        self.assertEqual(result['connected_deletions'],3)

    def test_outage_disconnected_pairs_remain_in_denominator(self):
        result = outage_conductance_analysis([(0,0),(1,0),(2,0)],[(0,1),(1,2)])
        for row in result['deletions']:
            self.assertAlmostEqual(row['mean_effective_conductance'],1/6,places=12)
            self.assertAlmostEqual(row['connected_pair_fraction'],1/3,places=12)
        self.assertEqual(result['disconnecting_deletions'],2)
        single = outage_conductance_analysis([(0,0),(1,0)],[(0,1)])
        self.assertEqual(single['mean_conductance_retention_fraction'],0)

    def test_outage_every_layout_matches_independent_grounded_reference(self):
        # All outages, including bridges and cycles; not a hand-picked subset.
        for graph in build_graphs():
            points, edges = graph['points'], graph['edges']
            _, _, _, weights = resistor_analysis(points, edges)
            result = outage_conductance_analysis(points, edges)
            for index, row in enumerate(result['deletions']):
                expected = grounded_outage_reference(points, edges, weights, index)
                self.assertAlmostEqual(row['mean_effective_conductance'],expected,places=9,msg=f"{graph['id']} {row['deleted_edge']}")
                self.assertGreaterEqual(row['conductance_retention_fraction'],0)
                self.assertLessEqual(row['conductance_retention_fraction'],1+1e-12)
            self.assertEqual(result['single_edge_failures_tested'],len(edges))

    def test_outage_scale_laws_and_edge_order_invariance(self):
        points = np.array([(0,0),(1,0),(1,1),(0,1)])
        edges = [(0,1),(1,2),(2,3),(0,3)]
        original = outage_conductance_analysis(points,edges)
        reordered = outage_conductance_analysis(points,list(reversed([(b,a) for a,b in edges])))
        self.assertEqual(original,reordered)
        scaled = outage_conductance_analysis(points*3,edges,volume=7,resistivity=2)
        self.assertAlmostEqual(scaled['mean_effective_conductance_after_one_edge_failure'],original['mean_effective_conductance_after_one_edge_failure']*7/18,places=12)
        self.assertAlmostEqual(scaled['mean_conductance_retention_fraction'],original['mean_conductance_retention_fraction'],places=12)

    def test_rerun_uses_actual_date_and_preserves_frozen_baseline(self):
        result = _module.run()
        self.assertEqual(result['run_date'],datetime.now(timezone.utc).date().isoformat())
        self.assertIsNotNone(datetime.fromisoformat(result['generated_utc']).tzinfo)
        self.assertFalse(result['edge_outages_requested'])
        frozen = json.loads((_module_path.parents[2] / 'evidence/geometry_transport_screen/20261004/results.json').read_text())
        for new, old in zip(result['graphs'],frozen['graphs']):
            self.assertEqual(new['id'],old['id'])
            self.assertEqual(new['nodes'],old['nodes'])
            self.assertEqual(new['edges'],old['edges'])
            for key in ('mean_effective_conductance','mean_effective_resistance','mean_path_stretch'):
                self.assertAlmostEqual(new['metrics'][key],old['metrics'][key],places=9)

if __name__=='__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--benchmark-outages':
        Path(sys.argv[2]).write_text(json.dumps(benchmark_outage_solvers(),indent=2,allow_nan=False)+'\n')
    else:
        unittest.main(verbosity=2)
