import importlib.util
from pathlib import Path
import unittest
import numpy as np

p = Path(__file__).with_name('run_stage5.py')
spec = importlib.util.spec_from_file_location('stage5_tested', p)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Stage5Tests(unittest.TestCase):
    def setUp(self):
        self.t = np.arange(0, 40*1800, 1800, dtype=np.int64)
        self.x = np.arange(40, dtype=float)+1
    def test_future_cannot_change_features(self):
        at = self.t[20:25]
        a = m.short_features(self.t, self.x, at, 1800.)
        z = self.x.copy(); z[25:] = 1e9
        np.testing.assert_array_equal(a, m.short_features(self.t, z, at, 1800.))
    def test_unknown_scenario_rejected(self):
        with self.assertRaises(ValueError): m.corrupt(self.t,self.x,'unknown',1,2025)
    def test_corruption_does_not_change_original_truth(self):
        original = self.x.copy(); m.corrupt(self.t,self.x,'missing_30pct',1,2025)
        np.testing.assert_array_equal(self.x,original)
    def test_corruption_deterministic(self):
        np.testing.assert_array_equal(m.corrupt(self.t,self.x,'missing_10pct',1,2025),m.corrupt(self.t,self.x,'missing_10pct',1,2025))
    def test_short_features_survive_missing_lags(self):
        z=self.x.copy(); z[18:20]=np.nan
        self.assertTrue(np.all(np.isfinite(m.short_features(self.t,z,self.t[20:21],1800.))))
    def test_missing_current_not_fabricated(self):
        z=self.x.copy(); z[20]=np.nan
        self.assertFalse(np.isfinite(m.short_features(self.t,z,self.t[20:21],1800.)[0,0]))
    def test_elapsed_mean_excludes_left_boundary(self):
        avg,_=m.partial_mean(self.t,self.x,self.t[4:5],3600,1800.)
        self.assertEqual(float(avg[0]),4.5)
    def test_bad_cadence_rejected(self):
        with self.assertRaises(ValueError): m.partial_mean(self.t,self.x,self.t,3600,0.)
    def test_same_intersection_for_all_methods(self):
        truth=np.ones(4); v1=np.ones((4,2)); v2=v1.copy(); v2[2,1]=np.nan
        np.testing.assert_array_equal(m.common_origins(truth,[v1,v2],np.ones(4,bool)),[True,True,False,True])
    def test_missing_truth_never_scored(self):
        np.testing.assert_array_equal(m.common_origins(np.array([1.,np.nan]),[np.ones((2,2))],np.ones(2,bool)),[True,False])
    def test_no_future_target_substitution_across_gap(self):
        t=np.array([0,1800,7200]);x=np.array([1.,2.,9.])
        self.assertTrue(np.isnan(m.s3.exact_target(t,x,np.array([1800]),3600)[0]))
    def test_partial_availability_fraction(self):
        z=self.x.copy();z[3]=np.nan
        avg,c=m.partial_mean(self.t,z,self.t[4:5],3600,1800.)
        self.assertEqual(float(avg[0]),5.);self.assertEqual(float(c[0]),.5)

if __name__=='__main__':unittest.main()
