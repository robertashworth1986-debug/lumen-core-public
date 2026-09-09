"""Synthetic source-bound replay tests for the Stage 6 report verifier."""
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import zipfile

import numpy as np


spec = importlib.util.spec_from_file_location(
    'stage6_verifier_test_subject', Path(__file__).with_name('verify_stage6.py'))
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
s6 = verifier.s6


class Stage6VerifierPrimitiveTests(unittest.TestCase):
    def test_json_duplicate_keys_refused_at_any_depth(self):
        for text in ('{"n": 1, "n": 2}', '{"x": {"n": 1, "n": 2}}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                verifier.strict_json(text, text=True)

    def test_json_nonfinite_literals_refused(self):
        for text in ('{"v": NaN}', '{"v": Infinity}', '{"v": -Infinity}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                verifier.strict_json(text, text=True)

    def test_boolean_gate_does_not_accept_number(self):
        for actual, expected in ((0, False), (1, True), (False, 0), (True, 1)):
            with self.subTest(actual=actual, expected=expected), self.assertRaises(ValueError):
                verifier.close(actual, expected, 'typed gate')

    def test_nonfinite_metric_refused(self):
        for actual in (float('nan'), float('inf'), float('-inf')):
            with self.assertRaises(ValueError):
                verifier.close(actual, .9, 'coverage')

    def test_empty_slice_has_no_invented_coverage(self):
        values = np.ones(3)
        result = verifier.descriptive_slice(values, values, values, np.zeros(3, bool))
        self.assertEqual((result['n'], result['hits'], result['misses']), (0, 0, 0))
        self.assertIsNone(result['coverage'])
        self.assertIsNone(result['coverage_deficit_percentage_points'])
        self.assertEqual(result['state'], 'INSUFFICIENT_REGIME_EVIDENCE')

    def test_slice_floor_does_not_promote_small_perfect_slice(self):
        y = np.ones(99)
        result = verifier.descriptive_slice(y, y, y, np.ones(99, bool))
        self.assertEqual(result['coverage'], 1.)
        self.assertEqual(result['state'], 'INSUFFICIENT_REGIME_EVIDENCE')

    def test_concentration_preserves_missing_exclusions_and_counts(self):
        y = np.array([2., 2., 2., 2., 2., np.nan])
        lo = np.zeros(6)
        hi = np.array([1., 1., 3., 3., 1., 1.])
        result = verifier.concentration(y, lo, hi, np.isfinite(y),
                                        np.array([True, True, True, False, False, True]))
        self.assertEqual(result['overall']['n'], 5)
        self.assertEqual(result['overall']['misses'], 3)
        self.assertEqual(result['high_at_issue']['misses'], 2)
        self.assertAlmostEqual(result['high_share_of_all_misses'], 2 / 3)
        self.assertAlmostEqual(result['high_to_ordinary_miss_rate_ratio'], 4 / 3)

    def test_zero_ordinary_misses_does_not_invent_finite_ratio(self):
        y = np.array([2., 2.])
        result = verifier.concentration(y, np.zeros(2), np.array([1., 3.]),
                                        np.ones(2, bool), np.array([True, False]))
        self.assertIsNone(result['high_to_ordinary_miss_rate_ratio'])


class Stage6VerifierFixtureTests(unittest.TestCase):
    """A complete 15-cell/240-record synthetic packet, never historical NOAA data."""

    @classmethod
    def setUpClass(cls):
        cls.fixture_temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture_temp.cleanup)
        cls.fixture = Path(cls.fixture_temp.name)
        prior = cls.fixture / 'prior'
        inputs = prior / 'results'
        inputs.mkdir(parents=True)
        results = cls.fixture / 'results'
        results.mkdir()
        at = s6.START + np.arange(180, dtype=np.int64) * 6 * 3600
        phase = np.arange(len(at))
        current = 10 + 2 * np.sin(phase / 8)
        prediction = 10 + np.sin(phase / 9)
        truth = prediction + 1.2 * np.cos(phase / 7)
        truth[11] = np.nan
        cfg = {'interval_initial_q90': 3., 'ridge': {'mean': [10.]},
               'high_activity_threshold': 10.5}
        records, comparisons, audits = [], [], []
        for sid in s6.STATIONS:
            for horizon in s6.HORIZONS:
                target = at + horizon * 60
                blend = prediction + .1
                router_result = s6.wrappers(at, target, truth, prediction, current, cfg, 1800)
                blend_result = s6.wrappers(at, target, truth, blend, current, cfg, 1800)
                columns = [at, target, truth, current, prediction, blend,
                           router_result['hi'][:, 0] - prediction,
                           blend_result['hi'][:, 0] - blend]
                names = 'issue_epoch,target_epoch,truth,persistence,delayed_router_v01,delayed_blend_v01,router_radius,blend_radius'
                np.savetxt(inputs / f'predictions_{sid}_{horizon}m.csv', np.column_stack(columns),
                           delimiter=',', header=names, comments='', fmt='%.17g')
                s6.write_json(inputs / f'calibration_{sid}_{horizon}m.json', cfg)
                r, c, a = s6.analyze_cell(prior, results, sid, horizon)
                records.extend(r)
                comparisons.extend(c)
                audits.append(a)
        cls.source = cls.fixture / 'source.zip'
        with zipfile.ZipFile(cls.source, 'w', compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(inputs.iterdir()):
                archive.write(path, 'results/' + path.name)
        cls.source_sha = s6.digest(cls.source)
        cls.source_bytes = cls.source.stat().st_size
        s6.write_json(results / 'interval_metrics.json', records)
        s6.write_json(results / 'comparisons.json', comparisons)
        s6.write_json(results / 'summary.json', {
            'schema_version': '1.0', 'experiment': 'stage6_interval_assurance_diagnostic_20260905',
            'protocol_commit': s6.PROTOCOL_COMMIT, 'source_sha256': cls.source_sha,
            'classification': 'REUSED_2025_ENGINEERING_DIAGNOSTIC', 'promotion_allowed': False,
            'interval_records': len(records), 'descriptive_comparisons': len(comparisons),
            'methods': s6.METHODS, 'point_models': s6.MODELS, 'cell_audits': audits,
            'paired_station_horizon_targets': sum(a['paired_origins'] for a in audits),
        })
        cls.columns = ['station', 'horizon_minutes', 'point_model', 'interval_method',
                       'feedback_delay_minutes', 'n', 'coverage', 'mean_width', 'interval_score',
                       'high_at_issue_n', 'high_at_issue_coverage']
        with (results / 'summary.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=cls.columns)
            writer.writeheader()
            for r in records:
                row = {name: r[name] for name in cls.columns[:5]}
                row.update({name: r['overall'][name] for name in cls.columns[5:9]})
                row.update(high_at_issue_n=r['high_at_issue']['n'],
                           high_at_issue_coverage=r['high_at_issue']['coverage'])
                writer.writerow(row)
        cls.seal(results)

    @staticmethod
    def seal(results):
        s6.write_json(results / 'SHA256_MANIFEST.json', {'files': [
            {'file': path.name, 'bytes': path.stat().st_size, 'sha256': s6.digest(path)}
            for path in sorted(results.iterdir()) if path.name != 'SHA256_MANIFEST.json'
        ]})

    def setUp(self):
        self.case_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.case_temp.cleanup)
        self.results = Path(self.case_temp.name) / 'results'
        shutil.copytree(self.fixture / 'results', self.results)
        self.sha_patch = mock.patch.object(s6, 'SOURCE_SHA', self.source_sha)
        self.bytes_patch = mock.patch.object(s6, 'SOURCE_BYTES', self.source_bytes)
        self.sha_patch.start()
        self.bytes_patch.start()
        self.addCleanup(self.sha_patch.stop)
        self.addCleanup(self.bytes_patch.stop)

    def verify(self):
        return verifier.verify_results(self.results, self.source)

    def mutate_json(self, name, mutation):
        path = self.results / name
        obj = json.loads(path.read_text())
        mutation(obj)
        s6.write_json(path, obj)
        self.seal(self.results)

    def test_full_synthetic_packet_recomputes_exactly(self):
        report = self.verify()
        self.assertEqual(report['interval_records_recomputed'], 240)
        self.assertEqual(report['comparison_records_recomputed'], 90)
        self.assertEqual(report['arrays_checked'], 465)
        self.assertEqual(report['paired_station_horizon_targets'], 179 * 15)
        self.assertTrue(report['interval_generation_replayed'])
        self.assertFalse(report['promotion_allowed'])
        self.assertFalse(report['independent_validation'])

    def test_missing_cell_cannot_hide_behind_unchanged_summary_count(self):
        self.mutate_json('interval_metrics.json', lambda rows: rows.pop())
        with self.assertRaises(ValueError):
            self.verify()

    def test_duplicate_cell_cannot_replace_another(self):
        self.mutate_json('comparisons.json', lambda rows: rows.__setitem__(-1, rows[0]))
        with self.assertRaises(ValueError):
            self.verify()

    def test_unknown_cell_refused(self):
        self.mutate_json('interval_metrics.json', lambda rows: rows[0].__setitem__('station', '99999'))
        with self.assertRaises(ValueError):
            self.verify()

    def test_promoted_record_refused(self):
        self.mutate_json('interval_metrics.json', lambda rows: rows[0].__setitem__('promotion_allowed', True))
        with self.assertRaises(ValueError):
            self.verify()

    def test_changed_metric_refused_after_manifest_reseal(self):
        self.mutate_json('interval_metrics.json', lambda rows: rows[0]['overall'].__setitem__('coverage', .123))
        with self.assertRaises(ValueError):
            self.verify()

    def test_frozen_truth_substitution_refused(self):
        path = self.results / 'intervals_41002_60m.npz'
        arrays = verifier.load_npz(path)
        arrays['truth'][0] += 1
        np.savez_compressed(path, **arrays)
        self.seal(self.results)
        with self.assertRaisesRegex(ValueError, 'Frozen input'):
            self.verify()

    def test_future_feedback_metadata_refused(self):
        path = self.results / 'intervals_41002_60m.npz'
        arrays = verifier.load_npz(path)
        arrays['delayed_router_v01_30m_latest'][0] = arrays['issue_epoch'][0]
        np.savez_compressed(path, **arrays)
        self.seal(self.results)
        with self.assertRaisesRegex(ValueError, 'feedback'):
            self.verify()

    def test_resealed_interval_bounds_fail_generation_replay(self):
        path = self.results / 'intervals_41002_60m.npz'
        arrays = verifier.load_npz(path)
        arrays['delayed_router_v01_30m_hi'][0, 1] += 1
        np.savez_compressed(path, **arrays)
        self.seal(self.results)
        with self.assertRaisesRegex(ValueError, '[Rr]eplay'):
            self.verify()

    def test_resealed_plausible_feedback_metadata_fails_replay(self):
        path = self.results / 'intervals_41002_60m.npz'
        arrays = verifier.load_npz(path)
        # This is within allowed alpha bounds and does not alter reported clipping rates.
        arrays['delayed_router_v01_30m_alpha'][0] = .11
        np.savez_compressed(path, **arrays)
        self.seal(self.results)
        with self.assertRaisesRegex(ValueError, '[Rr]eplay'):
            self.verify()

    def test_ci_requires_exactly_two_endpoints(self):
        self.mutate_json('comparisons.json', lambda rows: rows[0]['ci7_day_pct'].append(123.))
        with self.assertRaises(ValueError):
            self.verify()

    def test_null_metric_field_must_be_present(self):
        self.mutate_json('interval_metrics.json', lambda rows: rows[0].pop('alpha_at_bound_fraction'))
        with self.assertRaises(ValueError):
            self.verify()

    def test_summary_boolean_gate_requires_boolean(self):
        self.mutate_json('summary.json', lambda summary: summary.__setitem__('promotion_allowed', 0))
        with self.assertRaises(ValueError):
            self.verify()

    def test_csv_duplicate_header_refused(self):
        path = self.results / 'summary.csv'
        with path.open(newline='') as handle:
            rows = list(csv.reader(handle))
        # A duplicate coverage column containing the same value still violates the schema.
        with path.open('w', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(rows[0] + ['coverage'])
            writer.writerows(row + [row[6]] for row in rows[1:])
        self.seal(self.results)
        with self.assertRaises(ValueError):
            self.verify()


if __name__ == '__main__':
    unittest.main()
