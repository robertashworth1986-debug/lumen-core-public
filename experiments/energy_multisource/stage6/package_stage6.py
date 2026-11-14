"""Assemble verified Stage 6 evidence for the existing research-only publisher."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
REPO = 'robertashworth1986-debug/lumen-core-public'


def digest(p: Path) -> str:
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); out = a.out.resolve(); results = out / 'results'
    summary = json.loads((results / 'summary.json').read_text())
    if summary['interval_records'] != 240 or summary['descriptive_comparisons'] != 90 or summary['promotion_allowed'] is not False:
        raise ValueError('Result completeness or claim gate failed')
    rows = json.loads((results / 'SHA256_MANIFEST.json').read_text())['files']
    for row in rows:
        if Path(row['file']).name != row['file']:
            raise ValueError('Unsafe result path')
        p = results / row['file']
        if p.is_symlink() or p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
            raise ValueError('Result hash or size mismatch')
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if sha != os.environ['GITHUB_SHA'] or os.environ['GITHUB_REPOSITORY'] != REPO:
        raise ValueError('Executing checkout identity mismatch')
    if subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=ROOT, text=True).strip() != 'false':
        raise ValueError('Full Git ancestry required')
    subprocess.run(['git', 'merge-base', '--is-ancestor', '3e05c8d032352cba9dc107029bd9a7950b3eb7cb', sha], cwd=ROOT, check=True)
    source = out / 'inputs' / 'energy-stage4-ci.zip'
    if source.stat().st_size != 20736097 or digest(source) != summary['source_sha256']:
        raise ValueError('Frozen input archive mismatch')
    tests = (out / 'TESTS.txt').read_text()
    count = sum(int(v) for v in re.findall(r'^Ran (\d+) tests? in ', tests, re.MULTILINE))
    if count < 94 or 'FAILED (' in tests:
        raise ValueError('Expected inherited and new unit tests not complete')
    build = out / 'build'; build.mkdir(exist_ok=True)
    dist = out / 'dist'; dist.mkdir(exist_ok=True)
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
        'source_sha256': digest(source), 'result_manifest_sha256': digest(results / 'SHA256_MANIFEST.json')}
    (out / 'RUN_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    packet = dist / 'LumenCore_Energy_Stage6_20260905.zip'
    with zipfile.ZipFile(packet, 'w', compression=zipfile.ZIP_STORED) as z:
        z.write(source, 'inputs/' + source.name)
        for p in sorted(results.iterdir()):
            if p.is_file(): z.write(p, 'results/' + p.name)
        for p in sorted(build.iterdir()):
            if p.is_file(): z.write(p, p.name)
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
