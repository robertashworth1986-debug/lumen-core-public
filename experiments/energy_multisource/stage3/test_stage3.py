import unittest
import numpy as np
from run_stage3 import DAY, exact_target, rolling, ffill_limit, conservative_gate, boot_compare, holm

class IntegrityTests(unittest.TestCase):
    def test_elapsed_target_does_not_bridge_gaps_by_row_count(self):
        t=np.array([0,60,180,240]); x=np.array([1.,2.,3.,4.])
        y=exact_target(t,x,t,120)
        self.assertTrue(np.isnan(y[0])); self.assertEqual(y[1],3.)
    def test_missing_truth_is_never_filled(self):
        y=exact_target(np.array([0,60,120]),np.array([1.,np.nan,3.]),np.array([0]),60)
        self.assertTrue(np.isnan(y[0]))
    def test_no_future_value_enters_moving_average(self):
        t=np.arange(100)*60; x=np.arange(100,dtype=float); z=x.copy(); z[60:]=1e9
        np.testing.assert_equal(rolling(t,x,t[:60],300,60),rolling(t,z,t[:60],300,60))
    def test_rolling_checks_coverage(self):
        t=np.arange(10)*60; x=np.full(10,np.nan); x[-1]=1.
        self.assertTrue(np.isnan(rolling(t,x,np.array([540]),300,60)[0]))
    def test_forward_fill_is_bounded(self):
        x=ffill_limit(np.array([1.,np.nan,np.nan,np.nan]),2)
        np.testing.assert_equal(x[:3],[1.,1.,1.]);self.assertTrue(np.isnan(x[3]))
    def test_gate_never_consumes_unmatured_labels(self):
        at=np.arange(20*24)*3600; h=6*3600; p=np.ones(len(at))*10;r=np.zeros(len(at));truth=np.zeros(len(at))
        cutoff=12*DAY+3*3600
        changed=truth.copy(); changed[at+h>=cutoff]=1e8
        g=conservative_gate(at,truth,p,r,h); g2=conservative_gate(at,changed,p,r,h)
        np.testing.assert_equal(g[at<=cutoff],g2[at<=cutoff])
    def test_gate_falls_back_during_warmup(self):
        at=np.arange(20*24)*3600; p=np.ones(len(at))*10;r=np.zeros(len(at));truth=np.zeros(len(at))
        g=conservative_gate(at,truth,p,r,3600)
        self.assertFalse(g[at<5*DAY+3600].any());self.assertTrue(g[at>7*DAY].any())
    def test_gate_rejects_losing_candidate(self):
        at=np.arange(20*24)*3600;p=np.zeros(len(at));r=np.ones(len(at))*10;truth=np.zeros(len(at))
        self.assertFalse(conservative_gate(at,truth,p,r,3600).any())
    def test_zero_error_baseline_not_promoted(self):
        t=np.arange(10)*DAY;x=np.ones(10)
        r=boot_compare(t,x,x,x,3,5)
        self.assertIsNone(r['improvement_pct']);self.assertEqual(r['p_one_sided'],1.)
    def test_multiple_testing_includes_missing_cases(self):
        r={'p_one_sided':.001,'improvement_pct':10.,'ci95_pct':[1.,15.],'dataset':'NDBC_test'}
        holm([r]);self.assertAlmostEqual(r['holm_p'],.063);self.assertFalse(r['screen_pass'])
    def test_forensic_reanalysis_cannot_be_independent_validation(self):
        r={'p_one_sided':.00001,'improvement_pct':10.,'ci95_pct':[1.,15.],'dataset':'FORGE1683'}
        holm([r]);self.assertFalse(r['independent_validation']);self.assertEqual(r['confirmation_status'],'EXPLORATORY_ONLY')
    def test_bootstrap_repeatable(self):
        t=np.arange(30)*DAY;x=np.arange(30,dtype=float);p=x+5;r=x+4
        self.assertEqual(boot_compare(t,x,p,r,3,5),boot_compare(t,x,p,r,3,5))

if __name__=='__main__':unittest.main(verbosity=2)
