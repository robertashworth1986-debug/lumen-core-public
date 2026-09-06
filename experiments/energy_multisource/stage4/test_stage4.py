"""Adversarial integrity tests. No 2025 empirical outcomes are needed."""
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import run_stage4 as m


class Integrity(unittest.TestCase):
    def cfg(self):
        return {'champion': 0, 'prior_mae': [2.] * 7, 'interval_initial_q90': 3.}

    def stream(self):
        at = m.stamp(2025) + np.arange(48 * 24) * 1800
        truth = 10 + np.sin(np.arange(len(at)) / 30)
        E = np.column_stack([truth + v for v in [2, 1, 1.5, 2.5, 3, 4, 5]])
        return at, truth, E

    def test_exact_time_gap_never_compressed(self):
        np.testing.assert_equal(m.s3.exact_target(np.array([0, 1800, 9000]), np.array([1., 2., 3.]), np.array([0]), 3600), [np.nan])

    def test_missing_truth_not_imputed(self):
        np.testing.assert_equal(m.s3.exact_target(np.array([0, 3600]), np.array([1., np.nan]), np.array([0]), 3600), [np.nan])

    def test_target_direction(self):
        self.assertEqual(m.s3.exact_target(np.array([0, 3600]), np.array([1., 4.]), np.array([0]), 3600)[0], 4)

    def test_rolling_future_mutation(self):
        t = np.arange(100) * 1800; x = np.arange(100, dtype=float)
        at = t[:40]; a = m.s3.rolling(t, x, at, 3600, 1800)
        x[40:] += 9000
        np.testing.assert_equal(a, m.s3.rolling(t, x, at, 3600, 1800))

    def test_feedback_future_truth_mutation(self):
        t, y, E = self.stream(); a = m.adaptive(t, y, E, 3600, self.cfg())
        cutoff = m.stamp(2025, 1, 16); altered = y.copy(); altered[t + 3600 + 1800 >= cutoff] += 9999
        b = m.adaptive(t, altered, E, 3600, self.cfg())
        for k in ['pred', 'radius', 'chosen']:
            np.testing.assert_array_equal(a[k][t < cutoff], b[k][t < cutoff])

    def test_feedback_strictly_matured(self):
        t, y, E = self.stream(); a = m.adaptive(t, y, E, 21600, self.cfg())
        use = a['active']; self.assertTrue(np.all(a['latest_feedback_available'][use] < (t[use] // m.DAY) * m.DAY))

    def test_increased_latency_defers_learning(self):
        t, y, E = self.stream(); a = m.adaptive(t, y, E, 3600, self.cfg(), latency=100*m.DAY)
        self.assertFalse(a['active'].any())

    def test_warmup_is_champion(self):
        t, y, E = self.stream(); a = m.adaptive(t, y, E, 3600, self.cfg())
        np.testing.assert_equal(a['pred'][:48*4, 0], E[:48*4, 0])

    def test_blend_convex_hull(self):
        t, y, E = self.stream(); a = m.adaptive(t, y, E, 3600, self.cfg())['pred'][:, 1]
        self.assertTrue(np.all(a >= E.min(axis=1)-1e-10)); self.assertTrue(np.all(a <= E.max(axis=1)+1e-10))

    def test_router_chooses_existing_expert(self):
        t, y, E = self.stream(); a = m.adaptive(t, y, E, 3600, self.cfg())
        np.testing.assert_allclose(a['pred'][:, 0], E[np.arange(len(t)), a['chosen']])

    def test_missing_labels_do_not_teach(self):
        t, y, E = self.stream(); y[:] = np.nan
        self.assertFalse(m.adaptive(t, y, E, 3600, self.cfg())['active'].any())

    def test_empty_rejected(self):
        with self.assertRaises(ValueError): m.adaptive(np.array([]), np.array([]), np.empty((0, 7)), 3600, self.cfg())

    def test_duplicate_origins_rejected(self):
        t, y, E = self.stream(); t[1] = t[0]
        with self.assertRaises(ValueError): m.adaptive(t, y, E, 3600, self.cfg())

    def test_infinite_expert_rejected(self):
        t, y, E = self.stream(); E[5, 3] = np.inf
        with self.assertRaises(ValueError): m.adaptive(t, y, E, 3600, self.cfg())

    def test_training_mask_no_leak(self):
        rng = np.random.default_rng(1); X = rng.normal(size=(200, 3)); y = rng.normal(size=200); mask = np.arange(200)<120
        a = m.fit_ridge(X, y, mask); X[120:] += 10000; y[120:] += 10000
        self.assertEqual(a, m.fit_ridge(X, y, mask))

    def test_calibration_year_target_purge(self):
        t = np.arange(m.stamp(2023), m.stamp(2024), 3600); x = 10 + np.sin(np.arange(len(t)) / 30)
        a = m.calibrate(t, x, 21600)
        self.assertLess(a['last_selection_target'], m.stamp(2024))

    def test_constant_series(self):
        t = np.arange(m.stamp(2023), m.stamp(2024), 3600); x = np.full(len(t), 5.)
        a = m.calibrate(t, x, 3600); E, _ = m.expert_matrix(t, x, t, 3600, a['cadence_seconds'], a['ridge'])
        np.testing.assert_allclose(E, 5.)

    def test_hash_drift_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p/'x').write_text('old')
            (p/'SOURCE_MANIFEST.json').write_text(json.dumps({'files':[{'status':'ACQUIRED','file':'x','sha256':m.s3.digest(p/'x')}]}))
            m.verify_sources(p); (p/'x').write_text('new')
            with self.assertRaises(ValueError): m.verify_sources(p)

    def test_wrong_source_year_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.gz';p.write_bytes(gzip.compress(b'#YY MM DD hh mm WVHT APD\n2024 01 01 00 00 1 5\n'))
            with self.assertRaises(ValueError): m.s3.read_ndbc(p,2025)

    def test_duplicate_source_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.gz';p.write_bytes(gzip.compress(b'#YY MM DD hh mm WVHT APD\n2025 01 01 00 00 1 5\n2025 01 01 00 00 1 5\n'))
            with self.assertRaises(ValueError): m.s3.read_ndbc(p,2025)

    def test_missing_sentinel(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.gz';p.write_bytes(gzip.compress(b'#YY MM DD hh mm WVHT APD\n2025 01 01 00 00 99 5\n'))
            t,x,r=m.s3.read_ndbc(p,2025);self.assertTrue(np.isnan(x[0]))

    def test_multiplicity_uses_full_planned_family(self):
        r={'p_one_sided':.001,'n':10000,'scored_days':200,'common_pair_coverage':1.,'improvement_pct':10.,'ci95_pct':[1,20],'ci14_days':[1,20]}
        m.adjust([r]);self.assertAlmostEqual(r['holm_p'],.108);self.assertFalse(r['screen_pass'])

    def test_randomness_deterministic(self):
        t,y,E=self.stream();a=m.adaptive(t,y,E,3600,self.cfg());b=m.adaptive(t,y,E,3600,self.cfg())
        np.testing.assert_array_equal(a['pred'],b['pred'])

    def test_low_coverage_blocks_promotion(self):
        r={'p_one_sided':.0001,'n':10000,'scored_days':200,'common_pair_coverage':.5,'improvement_pct':10.,'ci95_pct':[1,20],'ci14_days':[1,20]}
        m.adjust([r]);self.assertFalse(r['screen_pass'])

if __name__ == '__main__': unittest.main(verbosity=2)
