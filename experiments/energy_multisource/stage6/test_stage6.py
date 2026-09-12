"""Synthetic invariants, not empirical evidence of performance."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile
import numpy as np

spec = importlib.util.spec_from_file_location('s6', Path(__file__).with_name('run_stage6.py'))
s6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(s6)

class Stage6Tests(unittest.TestCase):
    def series(self, days=8):
        t = s6.START + np.arange(days*48, dtype=np.int64)*1800
        p = 10 + np.sin(np.arange(len(t))/9)
        y = p + 2*np.cos(np.arange(len(t))/7)
        return t, t+3600, y, p, p.copy()

    def cfg(self):
        return {'interval_initial_q90': 3., 'ridge': {'mean': [10.]}}

    def run_case(self, data=None, delay=1800):
        return s6.wrappers(*(self.series() if data is None else data), self.cfg(), delay)

    def test_score_inside_is_width(self):
        self.assertEqual(s6.interval_score(np.array([2]), np.array([1]), np.array([3]))[0], 2)

    def test_score_lower_miss(self):
        self.assertEqual(s6.interval_score(np.array([0]), np.array([1]), np.array([3]))[0], 22)

    def test_score_upper_miss(self):
        self.assertEqual(s6.interval_score(np.array([5]), np.array([1]), np.array([3]))[0], 42)

    def test_bad_interval_refused(self):
        with self.assertRaises(ValueError): s6.interval_score(np.array([2]), np.array([3]), np.array([1]))

    def test_nonfinite_interval_refused(self):
        with self.assertRaises(ValueError): s6.interval_score(np.array([2]), np.array([1]), np.array([np.inf]))

    def test_finite_rank_upper(self):
        self.assertEqual(s6.finite_quantile(np.arange(10), .9), 9.)

    def test_finite_rank_lower(self):
        self.assertEqual(s6.finite_quantile(np.arange(20), .05, lower=True), 0.)

    def test_invalid_quantile_refused(self):
        for x, q in [(np.array([]), .9), (np.array([1, np.nan]), .9), (np.array([1]), 1)]:
            with self.assertRaises(ValueError): s6.finite_quantile(x, q)

    def test_duplicate_issue_refused(self):
        t, target, y, p, current = self.series(); t[1] = t[0]
        with self.assertRaises(ValueError): self.run_case((t, target, y, p, current))

    def test_past_target_refused(self):
        t, target, y, p, current = self.series(); target[0] = t[0]
        with self.assertRaises(ValueError): self.run_case((t, target, y, p, current))

    def test_infinite_truth_refused(self):
        data = self.series(); data[2][0] = np.inf
        with self.assertRaises(ValueError): self.run_case(data)

    def test_nonfinite_point_refused(self):
        data = self.series(); data[3][0] = np.nan
        with self.assertRaises(ValueError): self.run_case(data)

    def test_bad_initial_radius_refused(self):
        cfg = self.cfg(); cfg['interval_initial_q90'] = np.nan
        with self.assertRaises(ValueError): s6.wrappers(*self.series(), cfg, 1800)

    def test_all_missing_targets_never_filled(self):
        data = self.series(); data[2][:] = np.nan
        out = self.run_case(data)
        self.assertTrue(out['cold'].all()); self.assertTrue(np.all(out['latest'] == -1))
        self.assertTrue(np.isnan(data[2]).all())

    def test_future_truth_cannot_change_prior_bounds(self):
        data = self.series(); a = self.run_case(data)
        t, target, y, p, current = data; boundary = s6.START + 5*s6.DAY
        altered = y.copy(); altered[target >= boundary] += 1000
        b = self.run_case((t, target, altered, p, current))
        np.testing.assert_array_equal(a['lo'][t < boundary], b['lo'][t < boundary])
        np.testing.assert_array_equal(a['hi'][t < boundary], b['hi'][t < boundary])

    def test_own_unresolved_target_cannot_change_interval(self):
        data = self.series(); a = self.run_case(data)
        t, target, y, p, current = data; j = 245
        altered = y.copy(); altered[j] += 10000
        b = self.run_case((t, target, altered, p, current))
        np.testing.assert_array_equal(a['hi'][t <= target[j]+1800], b['hi'][t <= target[j]+1800])

    def test_strict_daily_maturity_both_delays(self):
        t = self.series()[0]
        for delay in [1800, 5400]:
            out = self.run_case(delay=delay); use = out['latest'] >= 0
            self.assertTrue(np.all(out['latest'][use] < (t[use]//s6.DAY)*s6.DAY))

    def test_longer_interval_delay_never_sees_newer_label(self):
        a, b = self.run_case(), self.run_case(delay=5400)
        self.assertTrue(np.all(b['latest'] <= a['latest']))

    def test_cold_start_is_same_for_all_methods(self):
        out = self.run_case()
        for i in range(1, 4): np.testing.assert_array_equal(out['hi'][:48, 0], out['hi'][:48, i])

    def test_all_bounds_nonnegative_and_ordered(self):
        out = self.run_case()
        self.assertTrue((out['lo'] >= 0).all()); self.assertTrue((out['hi'] >= out['lo']).all())

    def test_adaptive_alpha_bounded(self):
        out = self.run_case()
        self.assertTrue((out['alpha'] >= .02).all()); self.assertTrue((out['alpha'] <= .25).all())

    def test_no_input_mutation(self):
        data = self.series(); copies = [v.copy() for v in data]; self.run_case(data)
        for a, b in zip(data, copies): np.testing.assert_array_equal(a, b)

    def test_same_origin_metric_counts(self):
        t, target, y, p, current = self.series(); y[2] = np.nan
        out = self.run_case((t, target, y, p, current)); good = np.isfinite(y)
        counts = [s6.metrics(y, out['lo'][:, m], out['hi'][:, m], good)['n'] for m in range(4)]
        self.assertEqual(counts, [len(y)-1]*4)

    def test_empty_slice_is_not_zero_error(self):
        x = np.ones(3); result = s6.metrics(x, x, x, np.zeros(3, bool))
        self.assertIsNone(result['coverage']); self.assertIsNone(result['interval_score'])

    def test_constant_paired_bootstrap_gain(self):
        t = s6.START + np.arange(50)*s6.DAY
        for block in [7, 14]: np.testing.assert_allclose(s6.bootstrap_scores(t, np.ones(50)*10, np.ones(50)*9, block, 42), [10,10])

    def test_zip_path_traversal_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'bad.zip'
            with zipfile.ZipFile(path, 'w') as z: z.writestr('../escape', b'x')
            with self.assertRaises(ValueError): s6.safe_extract(path, Path(tmp)/'out')

    def test_duplicate_zip_member_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'bad.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('x', b'x'); z.writestr('x', b'y')
            with self.assertRaises(ValueError): s6.safe_extract(path, Path(tmp)/'out')

    def test_good_zip_extracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'good.zip'
            with zipfile.ZipFile(path, 'w') as z: z.writestr('data/file', b'x')
            s6.safe_extract(path, Path(tmp)/'out')
            self.assertEqual((Path(tmp)/'out/data/file').read_bytes(), b'x')

if __name__ == '__main__': unittest.main()
