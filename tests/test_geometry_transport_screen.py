import math, unittest
import numpy as np
import importlib.util
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

if __name__=='__main__': unittest.main(verbosity=2)
