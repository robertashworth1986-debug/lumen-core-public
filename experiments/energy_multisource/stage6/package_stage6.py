"""Assemble verified Stage 6 evidence for the existing research-only publisher."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
REPO = 'robertashworth1986-debug/lumen-core-public'
SOURCE_SHA = 'a0c693328a3a614ee7646731b81497f7d5f4b33b5338c9fab0595797d1017a2d'
SOURCE_BYTES = 20736097
RESULT_FILES = frozenset({
    'interval_metrics.json', 'comparisons.json', 'summary.csv', 'summary.json',
    *(f'intervals_{station}_{horizon}m.npz'
      for station in ('41002', '42001', '44025', '46050', '46237')
      for horizon in (60, 180, 360)),
})


def digest(p: Path) -> str:
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def strict_json(path: Path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key in packaging evidence')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('Nonfinite JSON value in packaging evidence')

    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=invalid)


def verify_result_inventory(results: Path) -> tuple[Path, ...]:
    """Require the complete declared packet, not a caller-selected hash subset."""
    if results.is_symlink() or not results.is_dir():
        raise ValueError('Invalid results directory')
    expected = RESULT_FILES | {'SHA256_MANIFEST.json'}
    observed = set()
    for path in results.iterdir():
        if path.is_symlink():
            raise ValueError('Symbolic result path')
        if path.name == 'verified_prior' and path.is_dir():
            continue  # Extraction cache is input evidence, never a result asset.
        if not path.is_file():
            raise ValueError('Unexpected non-file result entry')
        observed.add(path.name)
    if observed != expected:
        raise ValueError('Result directory does not match the exact file inventory')
    manifest = strict_json(results / 'SHA256_MANIFEST.json')
    rows = manifest.get('files') if isinstance(manifest, dict) else None
    if not isinstance(rows, list) or len(rows) != len(RESULT_FILES):
        raise ValueError('Result manifest does not list the complete inventory')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Invalid result manifest entry')
        name = row.get('file')
        if not isinstance(name, str) or name not in RESULT_FILES or name in seen:
            raise ValueError('Unexpected or duplicate result manifest path')
        seen.add(name)
        size, sha = row.get('bytes'), row.get('sha256')
        if (type(size) is not int or size < 0 or not isinstance(sha, str)
                or re.fullmatch(r'[0-9a-f]{64}', sha) is None):
            raise ValueError('Invalid result manifest size or digest')
        path = results / name
        if path.stat().st_size != size or digest(path) != sha:
            raise ValueError('Result hash or size mismatch')
    if seen != RESULT_FILES:
        raise ValueError('Result manifest inventory mismatch')
    return tuple(results / name for name in sorted(expected))


def verify_scientific_results(results: Path) -> dict:
    """Recompute the scientific records before assembling a publishable packet."""
    path = Path(__file__).with_name('verify_stage6.py')
    spec = importlib.util.spec_from_file_location('stage6_package_verifier', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_results(results)


def require_empty_output(path: Path) -> None:
    if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()))):
        raise ValueError('Packaging output already contains files; use a fresh directory')


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); out = a.out.resolve(); results = out / 'results'
    result_paths = verify_result_inventory(results)
    manifest_sha = digest(results / 'SHA256_MANIFEST.json')
    summary = strict_json(results / 'summary.json')
    if summary['interval_records'] != 240 or summary['descriptive_comparisons'] != 90 or summary['promotion_allowed'] is not False:
        raise ValueError('Result completeness or claim gate failed')
    verification = verify_scientific_results(results)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if sha != os.environ['GITHUB_SHA'] or os.environ['GITHUB_REPOSITORY'] != REPO:
        raise ValueError('Executing checkout identity mismatch')
    if subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=ROOT, text=True).strip() != 'false':
        raise ValueError('Full Git ancestry required')
    subprocess.run(['git', 'merge-base', '--is-ancestor', '3e05c8d032352cba9dc107029bd9a7950b3eb7cb', sha], cwd=ROOT, check=True)
    source = out / 'inputs' / 'energy-stage4-ci.zip'
    if (source.is_symlink() or source.stat().st_size != SOURCE_BYTES
            or digest(source) != SOURCE_SHA or summary['source_sha256'] != SOURCE_SHA):
        raise ValueError('Frozen input archive mismatch')
    tests = (out / 'TESTS.txt').read_text()
    count = sum(int(v) for v in re.findall(r'^Ran (\d+) tests? in ', tests, re.MULTILINE))
    if count < 134 or 'FAILED (' in tests:
        raise ValueError('Expected inherited and new unit tests not complete')
    build, dist = out / 'build', out / 'dist'
    require_empty_output(build)
    require_empty_output(dist)
    build.mkdir(exist_ok=True)
    dist.mkdir(exist_ok=True)
    subprocess.run(['git', 'archive', '--format=zip', '--output=' + str(build / 'research-code.zip'), sha,
        'experiments/energy_multisource', 'evidence/energy_continuity', 'evidence/energy_stage4',
        'ENERGY_BENCHMARK_STATUS.md', '.github/workflows'], cwd=ROOT, check=True)
    subprocess.run(['git', 'bundle', 'create', str(build / 'research-history.bundle'), 'HEAD'], cwd=ROOT, check=True)
    subprocess.run(['git', 'bundle', 'verify', str(build / 'research-history.bundle')], cwd=ROOT, check=True)
    ancestors = int(subprocess.check_output(['git', 'rev-list', '--count', 'HEAD'], cwd=ROOT, text=True))
    receipt = {'code_commit': sha, 'protocol_commit': summary['protocol_commit'],
        'run_id': int(os.environ['GITHUB_RUN_ID']), 'unit_tests_passed': count,
        'reachable_git_commits': ancestors, 'laptop_vps_history_audited': False,
        'interval_records': 240, 'descriptive_comparisons': 90, 'promotion_allowed': False,
        'source_sha256': digest(source), 'result_manifest_sha256': manifest_sha,
        'scientific_result_verification': verification}
    (out / 'RUN_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    packet = dist / 'LumenCore_Energy_Stage6_20260905.zip'
    with zipfile.ZipFile(packet, 'w', compression=zipfile.ZIP_STORED) as z:
        z.write(source, 'inputs/' + source.name)
        # A final inventory recheck catches additions or changed bytes since verification.
        if (verify_result_inventory(results) != result_paths
                or digest(results / 'SHA256_MANIFEST.json') != manifest_sha):
            raise ValueError('Result inventory changed during packaging')
        for p in result_paths:
            z.write(p, 'results/' + p.name)
        for name in ('research-code.zip', 'research-history.bundle'):
            z.write(build / name, name)
        for name in ['TESTS.txt', 'EXPERIMENT.log', 'RUN_RECEIPT.json']:
            z.write(out / name, name)
        z.write(Path(__file__).with_name('README.md'), 'README.md')
    if packet.stat().st_size >= 100_000_000:
        raise ValueError('Transfer packet exceeds declared single-file mirror bound')
    shutil.copyfile(Path(__file__).with_name('README.md'), dist / 'README.md')
    tag = 'research-energy-stage6-20260905-' + sha[:12]
    manifest = {'schema_version': '1.0', 'repository': REPO, 'code_commit': sha,
        'tag': tag, 'status': 'RESEARCH_ONLY_NO_PERFORMANCE_PROMOTION',
        'stage': 6, 'run_id': receipt['run_id'], 'continuity_issue': 214, 'review_pr': 215,
        'source_archive_included': True, 'full_reachable_git_ancestry_included': True,
        'files': [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)}
                  for p in sorted(dist.iterdir()) if p.is_file()]}
    (dist / 'CHECKPOINT_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (dist / 'SHA256SUMS.txt').write_text(''.join(digest(p) + '  ' + p.name + '\n'
        for p in sorted(dist.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.txt'))
    print(json.dumps({'packet_bytes': packet.stat().st_size, 'tag': tag, 'tests': count, 'promotion_allowed': False}))

if __name__ == '__main__': main()
