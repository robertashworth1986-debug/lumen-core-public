"""Adversarial packet-custody tests; no scientific performance claim."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location(
    'stage6_package_test_subject', Path(__file__).with_name('package_stage6.py'))
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class Stage6PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.results = self.root / 'results'
        self.results.mkdir()
        for name in package.RESULT_FILES:
            (self.results / name).write_bytes(name.encode('ascii'))
        (self.results / 'summary.json').write_text(json.dumps({
            'interval_records': 240, 'descriptive_comparisons': 90,
            'promotion_allowed': False, 'source_sha256': package.SOURCE_SHA,
        }))
        self.reseal()

    def reseal(self):
        self.rows = [
            {'file': p.name, 'bytes': p.stat().st_size, 'sha256': package.digest(p)}
            for p in sorted(self.results.iterdir())
            if p.is_file() and p.name != 'SHA256_MANIFEST.json'
        ]
        self.write_manifest(self.rows)

    def write_manifest(self, rows):
        (self.results / 'SHA256_MANIFEST.json').write_text(json.dumps({'files': rows}))

    def test_complete_inventory_returns_only_declared_assets(self):
        (self.results / 'verified_prior').mkdir()
        files = package.verify_result_inventory(self.results)
        self.assertEqual(len(files), 20)
        self.assertEqual({p.name for p in files}, package.RESULT_FILES | {'SHA256_MANIFEST.json'})

    def test_empty_manifest_cannot_attest_complete_summary(self):
        self.write_manifest([])
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_omitted_manifest_entry_refused(self):
        self.write_manifest(self.rows[:-1])
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_duplicate_entry_cannot_replace_missing_entry(self):
        self.write_manifest(self.rows[:-1] + [self.rows[0]])
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_duplicate_manifest_top_level_key_refused(self):
        (self.results / 'SHA256_MANIFEST.json').write_text(
            '{"files": [], "files": ' + json.dumps(self.rows) + '}')
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_duplicate_manifest_entry_key_refused(self):
        raw = json.dumps({'files': self.rows})
        raw = raw.replace('"bytes": ', '"bytes": 0, "bytes": ', 1)
        (self.results / 'SHA256_MANIFEST.json').write_text(raw)
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_nonfinite_json_extension_refused(self):
        (self.results / 'SHA256_MANIFEST.json').write_text(
            '{"ignored": NaN, "files": ' + json.dumps(self.rows) + '}')
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_missing_metrics_refused_even_after_self_consistent_reseal(self):
        (self.results / 'interval_metrics.json').unlink()
        self.reseal()
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_unmanifested_extra_file_refused(self):
        (self.results / 'old_result.json').write_text('{"promotion_allowed": true}')
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_manifested_extra_file_also_refused(self):
        (self.results / 'old_result.json').write_text('{}')
        self.reseal()
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_unexpected_directory_refused(self):
        (self.results / 'stale').mkdir()
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_same_length_changed_bytes_refused(self):
        path = self.results / 'comparisons.json'
        path.write_bytes(b'X' * path.stat().st_size)
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_boolean_byte_count_refused(self):
        self.rows[0]['bytes'] = True
        self.write_manifest(self.rows)
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_cross_platform_path_traversal_refused(self):
        for name in ('../outside', '..\\outside', '/absolute', 'C:outside'):
            rows = [dict(row) for row in self.rows]
            rows[0]['file'] = name
            self.write_manifest(rows)
            with self.subTest(name=name), self.assertRaises(ValueError):
                package.verify_result_inventory(self.results)

    def test_symbolic_result_refused(self):
        path = self.results / 'comparisons.json'
        target = self.root / 'outside.json'
        target.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError as exc:
            self.skipTest(f'Symlink creation unavailable: {exc}')
        with self.assertRaises(ValueError):
            package.verify_result_inventory(self.results)

    def test_empty_or_missing_packaging_directory_allowed(self):
        package.require_empty_output(self.root / 'new')
        empty = self.root / 'empty'
        empty.mkdir()
        package.require_empty_output(empty)

    def test_stale_packaging_directory_refused(self):
        stale = self.root / 'dist'
        stale.mkdir()
        (stale / 'old_private_notes.txt').write_text('Synthetic unapproved extra file')
        with self.assertRaises(ValueError):
            package.require_empty_output(stale)

    def test_semantic_verification_is_required_before_packaging_side_effects(self):
        # This fixture has valid custody hashes but deliberately invalid metric content.
        # The scientific verifier must be consulted before Git/archive/publication work.
        with mock.patch('sys.argv', ['package_stage6.py', '--out', str(self.root)]), \
                mock.patch.object(package, 'verify_scientific_results',
                                  side_effect=ValueError('Synthetic metrics rejected')) as verify, \
                mock.patch.object(package.subprocess, 'check_output') as git:
            with self.assertRaisesRegex(ValueError, 'Synthetic metrics rejected'):
                package.main()
            verify.assert_called_once_with(self.results)
            git.assert_not_called()
        self.assertFalse((self.root / 'build').exists())
        self.assertFalse((self.root / 'dist').exists())


if __name__ == '__main__':
    unittest.main()
