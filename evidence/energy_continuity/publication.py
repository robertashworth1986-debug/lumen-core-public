"""Verified draft-by-ID publication; exact one-checkpoint resume is explicitly pinned.

The only external write is PATCH of the verified research release's draft state.
Normal first publication may create a new draft; resume never creates/uploads assets.
No branch mutation, credential printing, production or latest-release promotion.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('custody_base', HERE/'checkpoint.py')
assert spec is not None and spec.loader is not None
custody = importlib.util.module_from_spec(spec); spec.loader.exec_module(custody)
REPO = custody.REPO
KNOWN = {
    'release_id': 383284902,
    'code_commit': '584e88a0f376ca016a085077047052d406081f98',
    'tag': 'research-energy-20260905-584e88a0f376',
    'package_id': 9971930681,
    'package_sha256': 'bf58d106fafdee5b9b67496f3067044907c1ab3d0e8eac188b554a8452f6bdc2',
    'manifest_sha256': 'f9b332d32bbba33e009c4a61522ff9d507cbd55f7b1121e30b96c9adb9cb35c9',
}


def choose_release(rows: list[dict], tag: str) -> dict | None:
    matches = [r for r in rows if r.get('tag_name') == tag]
    if len(matches) > 1:
        raise ValueError('Ambiguous release identity; no mutation permitted')
    return matches[0] if matches else None


def lookup_release(tag: str, release_id: int | None = None) -> dict | None:
    # Drafts are discovered through the collection or a numeric ID, not /tags/.
    if release_id is not None:
        result = custody.gh_json(f'repos/{REPO}/releases/{release_id}')
        if result.get('id') != release_id or result.get('tag_name') != tag:
            raise ValueError('Pinned draft ID/tag mismatch')
        return result
    for page in range(1, 11):
        rows = custody.gh_json(f'repos/{REPO}/releases?per_page=100&page={page}')
        result = choose_release(rows, tag)
        if result is not None:
            return custody.gh_json(f'repos/{REPO}/releases/{result["id"]}')
        if len(rows) < 100:
            return None
    raise ValueError('Release lookup bound exhausted; do not create a duplicate')


def validate_release(release: dict, tag: str, sha: str, expected: dict, notes: str) -> None:
    if release.get('tag_name') != tag or release.get('target_commitish') != sha or release.get('prerelease') is not True:
        raise ValueError('Research release identity/type mismatch')
    if release.get('body', '').strip() != notes.strip():
        raise ValueError('Research claim-boundary notes mismatch')
    assets = {r['name']: r for r in release['assets']}
    if len(assets) != len(release['assets']) or set(assets) != set(expected):
        raise ValueError('Release asset set mismatch; not overwritten')
    for name, row in assets.items():
        if row.get('state') != 'uploaded' or row['size'] != expected[name]['bytes'] or row.get('digest') != 'sha256:'+expected[name]['sha256']:
            raise ValueError('Uploaded asset byte/hash mismatch')


def publish(out: Path, resume_known: bool = False) -> dict:
    dist = out/'dist'
    manifest = json.loads((dist/'CHECKPOINT_MANIFEST.json').read_text())
    tag, sha = manifest['tag'], manifest['code_commit']
    publisher = os.environ['GITHUB_SHA']
    if os.environ.get('GITHUB_REPOSITORY') != REPO or manifest['repository'] != REPO:
        raise ValueError('Repository mismatch')
    if resume_known:
        if sha != KNOWN['code_commit'] or tag != KNOWN['tag'] or custody.digest(out/'transfer.zip') != KNOWN['package_sha256'] or custody.digest(dist/'CHECKPOINT_MANIFEST.json') != KNOWN['manifest_sha256']:
            raise ValueError('Pinned resume package identity mismatch')
    elif sha != publisher:
        raise ValueError('Normal publication must match executing code commit')
    expected = {p.name: {'bytes': p.stat().st_size, 'sha256': custody.digest(p)} for p in sorted(dist.iterdir()) if p.is_file()}
    wanted = {r['file'] for r in manifest['files']} | {'CHECKPOINT_MANIFEST.json', 'SHA256SUMS.txt'}
    if set(expected) != wanted or manifest['status'] != 'RESEARCH_ONLY_NO_PERFORMANCE_PROMOTION':
        raise ValueError('Local package/claim state mismatch')
    for row in manifest['files']:
        if Path(row['file']).name != row['file']:
            raise ValueError('Unsafe manifest path')
        custody.verify_file(dist/row['file'], row)
    notes = (dist/'README.md').read_text()
    release = lookup_release(tag, KNOWN['release_id'] if resume_known else None)
    if release is None:
        if resume_known:
            raise ValueError('Pinned draft unavailable; no replacement authorized')
        subprocess.run(['gh','release','create',tag,*[str(dist/n) for n in expected],'-R',REPO,
            '--target',sha,'--draft','--prerelease','--latest=false',
            '--title','RESEARCH ONLY: energy benchmark checkpoint 2026-09-05',
            '--notes-file',str(dist/'README.md')],check=True,timeout=600)
        release = lookup_release(tag)
    if release is None:
        raise ValueError('Created draft unavailable; no publication inferred')
    validate_release(release, tag, sha, expected, notes)
    release_id = int(release['id'])
    if release['draft']:
        # Use the verified numeric release ID; PATCH only publication flags.
        c = subprocess.run(['gh','api','--method','PATCH',f'repos/{REPO}/releases/{release_id}','--input','-'],
            input=json.dumps({'draft':False,'prerelease':True,'make_latest':'false'}),
            capture_output=True,text=True,timeout=120)
        if c.returncode:
            raise RuntimeError('Draft publication failed; existing draft and assets retained')
    verified = custody.gh_json(f'repos/{REPO}/releases/{release_id}')
    validate_release(verified, tag, sha, expected, notes)
    ref = custody.gh_json(f'repos/{REPO}/git/ref/tags/{tag}')
    if verified['draft'] or ref['object']['type'] != 'commit' or ref['object']['sha'] != sha:
        raise ValueError('Published release/tag read-back failed')
    receipt = {'schema_version':'1.1','status':'PUBLISHED_RESEARCH_PRERELEASE',
        'release_url':verified['html_url'],'release_id':release_id,'tag':tag,
        'code_commit':sha,'publisher_commit':publisher,
        'publication_run_id':int(os.environ['GITHUB_RUN_ID']),
        'publication_run_attempt':int(os.environ['GITHUB_RUN_ATTEMPT']),
        'resumed_existing_draft':resume_known,'verified_asset_count':len(expected),
        'verified_assets':expected,'main_modified':False,'production_deployed':False,
        'new_performance_claim_authorized':False}
    (out/'PUBLICATION_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'publication':verified['html_url'],'verified_assets':len(expected)}))
    return receipt


def main() -> None:
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--resume-known',action='store_true');a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    try:
        publish(a.out,a.resume_known)
    except Exception as exc:
        # Preserve a safe failure receipt without exception payloads or credentials.
        (a.out/'PUBLICATION_FAILURE.json').write_text(json.dumps({'status':'PUBLICATION_FAILED',
            'exception_type':type(exc).__name__,'publisher_commit':os.environ.get('GITHUB_SHA'),
            'resume_known':a.resume_known,'existing_assets_not_overwritten':True},indent=2)+'\n')
        raise

if __name__=='__main__':main()
