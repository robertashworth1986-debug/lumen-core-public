import unittest
import json
import numpy as np
import run_diagnostic as d


class OverlayTests(unittest.TestCase):
    def fixture(self, n=240):
        at = np.arange(n, dtype=np.int64)*1800
        return dict(at=at, target=at+3600, truth=np.full(n, 50.),
                    prediction=np.full(n, 10.), current=np.full(n, 10.),
                    base_lo=np.full(n, 9.), base_hi=np.full(n, 11.), threshold=5., mean=10.)

    def test_future_outcomes_cannot_change_earlier_intervals(self):
        x = self.fixture()
        first = d.overlay(**x)
        cutoff = 3*d.DAY
        altered = x.copy(); altered['truth'] = x['truth'].copy()
        altered['truth'][x['target']+d.DELAY >= cutoff] = 100000.
        second = d.overlay(**altered)
        earlier = x['at'] < cutoff
        for name in first:
            np.testing.assert_array_equal(first[name][earlier], second[name][earlier])

    def test_outcome_at_boundary_is_not_available(self):
        x = self.fixture()
        baseline = d.overlay(**x)
        index = np.flatnonzero(x['target']+d.DELAY == d.DAY)[0]
        x['truth'][index] = 999999.
        result = d.overlay(**x)
        same_day = x['at']//d.DAY == 1
        np.testing.assert_array_equal(result['hi'][same_day], baseline['hi'][same_day])
        self.assertTrue((result['latest_maturity'][same_day] < d.DAY).all())

    def test_insufficient_history_falls_back(self):
        x = self.fixture(n=31)
        r = d.overlay(**x)
        np.testing.assert_array_equal(r['lo'], x['base_lo'])
        np.testing.assert_array_equal(r['hi'], x['base_hi'])
        self.assertFalse(r['supported_high_issue'].any())

    def test_ordinary_issues_exactly_unchanged(self):
        x = self.fixture(); x['current'][170:] = 1.
        r = d.overlay(**x)
        np.testing.assert_array_equal(r['lo'][170:], x['base_lo'][170:])
        np.testing.assert_array_equal(r['hi'][170:], x['base_hi'][170:])

    def test_overlay_cannot_narrow(self):
        x = self.fixture(); r = d.overlay(**x)
        self.assertTrue((r['lo'] <= x['base_lo']).all())
        self.assertTrue((r['hi'] >= x['base_hi']).all())
        self.assertTrue((r['hi'] > x['base_hi']).any())

    def test_nan_truth_does_not_enter_calibration(self):
        x = self.fixture(); x['truth'][:100] = np.nan
        r = d.overlay(**x)
        self.assertEqual(r['calibration_n'][96], 0)

    def test_expired_history_is_excluded(self):
        x = self.fixture(n=34); x['at'][-1] = 30*d.DAY; x['target'][-1] = x['at'][-1]+3600
        r = d.overlay(**x)
        self.assertEqual(r['calibration_n'][-1], 0)

    def test_quantile_rank_is_capped_for_small_n(self):
        self.assertEqual(d.quantile_upper([7.]), 7.)
        self.assertEqual(d.quantile_upper([1., 2.]), 2.)
        self.assertEqual(d.quantile_upper(np.arange(32.)), 29.)

    def test_malformed_inputs_rejected(self):
        for change in [{'threshold': np.nan}, {'mean': 0.}, {'base_hi': np.zeros(240)},
                       {'target': np.zeros(240)}, {'truth': np.full(240, np.inf)},
                       {'prediction': np.ones((240, 1))}]:
            with self.subTest(change=list(change)):
                x = self.fixture(); x.update(change)
                with self.assertRaises(ValueError): d.overlay(**x)

    def test_empty_slice_remains_empty(self):
        x = self.fixture(); m = d.metrics(x['truth'], x['base_lo'], x['base_hi'], np.zeros(240, bool))
        self.assertEqual(m['n'], 0); self.assertIsNone(m['coverage'])

    def test_protocol_disagreement_is_rejected(self):
        p = json.loads((d.HERE/'PROTOCOL.json').read_text()); d.validate_protocol(p)
        p['minimum_matured_high_regime_residuals'] = 16
        with self.assertRaises(ValueError): d.validate_protocol(p)


if __name__ == '__main__':
    unittest.main()
