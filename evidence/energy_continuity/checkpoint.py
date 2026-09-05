"""Bounded research preservation. Explicit archive acquisition/package/publication.

Does not push branches, alter main, deploy, access user secrets, or overwrite assets.
The publication command needs the Actions token only in its own workflow step.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = Path(__file__).with_name('ARCHIVE_PLAN.json')
REPO = 'robertashworth1986-debug/lumen-core-public'


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()


def checked_zip(p: Path) -> list[str]:
    with zipfile.ZipFile(p) as z:
        infos = z.infolist(); seen = set()
        if len(infos) > 20000 or sum(i.file_size for i in infos) > 512*1024*1024:
            raise ValueError('Archive resource bound exceeded')
        for i in infos:
            q = PurePosixPath(i.filename)
            if q.is_absolute() or '..' in q.parts or '\\' in i.filename or ':' in i.filename or i.filename in seen:
                raise ValueError('Unsafe or duplicate archive path')
            if stat.S_ISLNK(i.external_attr >> 16): raise ValueError('Archive symlink rejected')
            seen.add(i.filename)
        if z.testzip() is not None: raise ValueError('Archive CRC failure')
        return [i.filename for i in infos]


def verify_file(p: Path, row: dict) -> None:
    if p.is_symlink() or not p.is_file() or p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
        raise ValueError('Artifact byte/hash identity mismatch')


def gh_json(path: str) -> dict:
    c = subprocess.run(['gh','api',path], capture_output=True, text=True, timeout=120)
    if c.returncode: raise RuntimeError('GitHub read failed; no success inferred')
    return json.loads(c.stdout)


def acquire(out: Path, local: Path | None) -> None:
    plan = json.loads(PLAN_PATH.read_text())
    if plan['repository'] != REPO: raise ValueError('Unexpected archive repository')
    folder = out/'archives'; folder.mkdir(parents=True, exist_ok=True)
    for r in plan['artifacts']:
        if Path(r['file']).name != r['file']: raise ValueError('Bad archive filename')
        p = folder/r['file']
        if not p.exists():
            if local:
                verify_file(local/r['file'], r); shutil.copyfile(local/r['file'], p)
            else:
                meta = gh_json(f'repos/{REPO}/actions/artifacts/{r["artifact_id"]}')
                if meta['expired'] or meta['workflow_run']['id'] != r['run_id'] or meta['digest'] != 'sha256:'+r['sha256']:
                    raise ValueError('Wrong/expired upstream artifact metadata')
                with p.open('xb') as f:
                    c = subprocess.run(['gh','api',f'repos/{REPO}/actions/artifacts/{r["artifact_id"]}/zip'], stdout=f, stderr=subprocess.PIPE, timeout=240)
                if c.returncode: raise RuntimeError('Artifact download failed; partial bytes retained')
        verify_file(p, r); checked_zip(p)
        print('verified', r['file'], flush=True)
    prior = out/'prior'; prior.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(folder/'energy-stage4-ci.zip') as z: z.extractall(prior)
    (out/'ACQUISITION_RECEIPT.json').write_text(json.dumps({'verified_archives':len(plan['artifacts']),
        'plan_sha256':digest(PLAN_PATH),'source_bytes':sum(r['bytes'] for r in plan['artifacts'])},indent=2)+'\n')


def package(out: Path) -> None:
    summary = json.loads((out/'results/summary.json').read_text())
    if summary['diagnostic_records'] != 600 or summary['promotion_allowed'] is not False:
        raise ValueError('Diagnostic completeness/claim gate failed')
    rows = json.loads((out/'results/SHA256_MANIFEST.json').read_text())['files']
    for r in rows:
        if Path(r['file']).name != r['file']: raise ValueError('Bad result path')
        verify_file(out/'results'/r['file'], r)
    sha = subprocess.check_output(['git','rev-parse','HEAD'], text=True, cwd=ROOT).strip()
    if sha != os.environ['GITHUB_SHA']: raise ValueError('Checkout/runner SHA mismatch')
    if subprocess.check_output(['git','rev-parse','--is-shallow-repository'], text=True,cwd=ROOT).strip() != 'false':
        raise ValueError('History preservation requires complete ancestry')
    subprocess.run(['git','merge-base','--is-ancestor','a369e1ce658faf89d67e26ed36c85d3d69cccf41',sha],check=True,cwd=ROOT)
    dist = out/'dist'; dist.mkdir(parents=True,exist_ok=True)
    plan = json.loads(PLAN_PATH.read_text())
    for r in plan['artifacts']:
        verify_file(out/'archives'/r['file'],r)
        shutil.copyfile(out/'archives'/r['file'],dist/r['file'])
    with zipfile.ZipFile(dist/'stage5-results.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted((out/'results').iterdir()):
            if p.is_file(): z.write(p,'results/'+p.name)
        for name in ['TESTS_STAGE3.txt','TESTS_STAGE4.txt','TESTS_STAGE5.txt','TESTS_CUSTODY.txt','ACQUISITION_RECEIPT.json','EXPERIMENT.log']:
            z.write(out/name,name)
    subprocess.run(['git','archive','--format=zip','--output='+str((dist/'research-code.zip').resolve()),sha,
        'experiments/energy_multisource','experiments/geothermal','evidence/energy_stage4',
        'evidence/energy_continuity','ENERGY_BENCHMARK_STATUS.md','.github/workflows'],check=True,cwd=ROOT)
    subprocess.run(['git','bundle','create',str((dist/'research-history.bundle').resolve()),'HEAD'],check=True,cwd=ROOT)
    subprocess.run(['git','bundle','verify',str((dist/'research-history.bundle').resolve())],check=True,cwd=ROOT)
    count = int(subprocess.check_output(['git','rev-list','--count','HEAD'],text=True,cwd=ROOT))
    shutil.copyfile(ROOT/'ENERGY_BENCHMARK_STATUS.md',dist/'README.md')
    shutil.copyfile(PLAN_PATH,dist/'ARCHIVE_PLAN.json')
    tag='research-energy-20260905-'+sha[:12]
    manifest={'schema_version':'1.0','repository':REPO,'code_commit':sha,'tag':tag,
        'run_id':int(os.environ['GITHUB_RUN_ID']),'run_attempt':int(os.environ['GITHUB_RUN_ATTEMPT']),
        'continuity_issue':214,'review_pr':215,'prior_archives':9,'diagnostic_records':600,
        'history_ancestor_commits':count,'local_laptop_vps_history_audited':False,
        'status':'RESEARCH_ONLY_NO_PERFORMANCE_PROMOTION','files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':digest(p)}
            for p in sorted(dist.iterdir()) if p.is_file() and p.name not in ('CHECKPOINT_MANIFEST.json','SHA256SUMS.txt')]}
    (dist/'CHECKPOINT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (dist/'SHA256SUMS.txt').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in sorted(dist.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
    (out/'PACKAGE_RECEIPT.json').write_text(json.dumps({'tag':tag,'code_commit':sha,'assets':len(list(dist.iterdir())),
        'history_ancestor_commits':count,'manifest_sha256':digest(dist/'CHECKPOINT_MANIFEST.json')},indent=2)+'\n')


def publish(out: Path) -> None:
    dist = out/'dist'; manifest=json.loads((dist/'CHECKPOINT_MANIFEST.json').read_text())
    tag,sha = manifest['tag'],manifest['code_commit']
    if sha != os.environ['GITHUB_SHA'] or os.environ.get('GITHUB_REPOSITORY') != REPO:
        raise ValueError('Publication identity mismatch')
    expected={p.name:{'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(dist.iterdir()) if p.is_file()}
    for r in manifest['files']: verify_file(dist/r['file'],r)
    c=subprocess.run(['gh','api',f'repos/{REPO}/releases/tags/{tag}'],capture_output=True,text=True,timeout=120)
    if c.returncode:
        if 'HTTP 404' not in c.stderr: raise RuntimeError('Release lookup failed')
        subprocess.run(['gh','release','create',tag,*[str(dist/n) for n in expected],'-R',REPO,
            '--target',sha,'--draft','--prerelease','--latest=false','--title','RESEARCH ONLY: energy benchmark checkpoint 2026-09-05',
            '--notes-file',str(dist/'README.md')],check=True,timeout=600)
    release=gh_json(f'repos/{REPO}/releases/tags/{tag}')
    if release['target_commitish'] != sha or not release['prerelease']:
        raise ValueError('Existing release identity/claim type mismatch; not overwritten')
    assets={r['name']:r for r in release['assets']}
    if set(assets) != set(expected): raise ValueError('Release asset set mismatch; draft remains unpublished')
    for name,r in assets.items():
        if r['size'] != expected[name]['bytes'] or r.get('digest') != 'sha256:'+expected[name]['sha256']:
            raise ValueError('Uploaded asset digest mismatch; no publication authorized')
    if release['draft']:
        subprocess.run(['gh','release','edit',tag,'-R',REPO,'--draft=false','--prerelease','--latest=false'],check=True,timeout=120)
    verified=gh_json(f'repos/{REPO}/releases/tags/{tag}')
    ref=gh_json(f'repos/{REPO}/git/ref/tags/{tag}')
    if verified['draft'] or not verified['prerelease'] or ref['object']['type']!='commit' or ref['object']['sha']!=sha:
        raise ValueError('Publication/tag read-back failed')
    (out/'PUBLICATION_RECEIPT.json').write_text(json.dumps({'status':'PUBLISHED_RESEARCH_PRERELEASE',
        'release_url':verified['html_url'],'release_id':verified['id'],'tag':tag,'code_commit':sha,
        'verified_asset_count':len(assets),'verified_assets':expected,'main_modified':False,'production_deployed':False},indent=2)+'\n')
    print(json.dumps({'publication':verified['html_url'],'verified_assets':len(assets)}))


def main() -> None:
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['acquire','package','publish']);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--local-archives',type=Path);a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
    if a.action=='acquire':acquire(a.out,a.local_archives)
    elif a.action=='package':package(a.out)
    else:publish(a.out)

if __name__=='__main__':main()
