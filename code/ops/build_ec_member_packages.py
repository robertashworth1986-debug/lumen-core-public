#!/usr/bin/env python3
"""Reproducible, explicit-file member packages; no vault, env or runtime data."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'dashboard/cohort/downloads'
FILES={
    'luma_runtime.py':'code/ec_member_runtime.py',
    'lib/audit_paper_accounting.py':'code/ops/audit_paper_accounting.py',
    'lib/grants_autofill.py':'code/grants_autofill.py',
    'public/cohort/index.html':'dashboard/cohort/index.html',
    'public/cohort/studio.css':'dashboard/cohort/studio.css',
    'public/cohort/studio.js':'dashboard/cohort/studio.js',
    'public/cohort/core.js':'dashboard/cohort/core.js',
    'public/build_week/prooflock_console/three.module.min.js':'dashboard/build_week/prooflock_console/three.module.min.js',
    'public/build_week/prooflock_console/three.core.min.js':'dashboard/build_week/prooflock_console/three.core.min.js',
    'public/cohort/mark.svg':'dashboard/cohort/mark.svg',
}

def readme(profile):
    name=profile['name'];slug=profile['id']
    return f'''{name} — EC Strength Studio
Our strength is making everyone else stronger.

WHAT YOU RECEIVED
A free LumenCore contribution for TakeOff Fall 2026. The public profile and
three workflow questions are independent research, open to your correction.
This is not an EC endorsement or an official site operated by {name}.

START ON WINDOWS
Install Python 3.11 or newer from https://www.python.org/downloads/ if needed.
Open PowerShell in this extracted folder (right click > Open in Terminal),
then copy this command:

    python .\luma_runtime.py --member {slug}

Open the address printed in the terminal:
    http://127.0.0.1:8766/cohort/?member={slug}

On macOS or Linux use: python3 ./luma_runtime.py --member {slug}
No pip packages are required. Keep the terminal open; Ctrl+C stops the app.
If port 8766 is in use, add --port 8767 and use the printed address.

USE YOUR OWN AI KEY (OPTIONAL)
The workboard, measurement sheets, grant drafts, scout and paper tools work
without an AI key. The assistant uses your process OPENAI_API_KEY if set.
Your provider bills your own API usage. No key or paid subscription is included.
The key is never served to your browser or saved by this app.
For a temporary PowerShell session, enter your own key through a hidden prompt:

    $LumaSecret = Read-Host 'Your OpenAI API key' -AsSecureString
    $LumaPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($LumaSecret)
    try {{
        $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($LumaPointer)
    }} finally {{
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($LumaPointer)
    }}
    python .\luma_runtime.py --member {slug}
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue

The default model is gpt-6-astra. Set LUMA_OPENAI_MODEL in the same terminal
only if your account requires another supported Responses model. AI is limited
to four requests per hour and 1,800 output tokens per request. A failed or
timed-out request may still incur provider usage; the app does not retry it.

WHAT THE TOOLS DO
- Workboard: briefs, acceptance criteria, owner review, dates and file hashes.
- Measure & improve: record observations and compare full-batch energy for
  equivalent accepted output. Failed work, rework and overhead remain included.
- Grant Factory: turn your supplied facts into Markdown drafts. Unknowns remain
  marked. No applicant attributes, eligibility, signatures or awards are invented.
- LumaScout: retrieve public Grants.gov listings; rank keywords, not eligibility.
- Paper Lab: simulate a 5/20 moving-average rule on fabricated or imported daily
  CSV prices. The optional local paper bot reads public BTC-USD quotes hourly,
  starts with 10,000 fictional USD, uses a 25% cash allocation, modeled 10 bps
  fees and 5 bps slippage, and reconciles its own paper ledger. No broker orders.
- LumaCare: practice nonclinical handoffs with fictional/non-sensitive IDs only.
- Assistant: sends your explicit prompt and public company context to OpenAI.
  It cannot access your workboard, customer files, clinical systems or accounts.

SCHEDULED WORK
The assistant, scout and paper screens show local task controls. You can enable
hourly public grant checks or the paper bot. The first scheduled run is one hour
after enabling. Tasks run only while this Python process stays open. Each run
records a success or failure, source receipts where applicable and a local
integrity-chain entry. Failed tasks do not become completed results.

YOUR DATA AND BACKUPS
The public page keeps entries in this browser. This local runtime also saves a
member-specific backup in .luma_data/{slug}/workspace.sqlite3. Its journal files
are in the same folder. Use Export workspace to move data between computers;
Your free package > Import a backup loads the matching member's backup.
If this browser and the local backup contain different records, automatic
backup pauses. Choose Review saved versions to download either version and
select which records to keep. Two simultaneous sessions cannot silently
overwrite each other's local backup. Closing the notice leaves backup paused.
Keep the entire .luma_data folder private. It is ordinary local storage, not an
encrypted clinical database. Do not enter patient identifiers, diagnoses, secrets,
bank details or sensitive customer records. Revision files never leave the
browser; only their selected name and SHA-256 are stored.

The server binds only to 127.0.0.1 and rejects cross-origin API requests. It has
no remote accounts, email dispatch, grant submission, live-trade or equipment
control route. Team access and regulated data require a separate owner-approved
deployment and review. Government certification and HIPAA compliance are not
established by this package. Trading results are modeled, not profit evidence.

SOURCE AND REVIEW
Your three specific workflow hypotheses and source URLs: member-research.json
Package contents and hashes: package-manifest.json
Repository: https://github.com/robertashworth1986-debug/lumen-core-public
Public gift: https://lumen-core.ai/cohort/?member={slug}
Public strength profile: https://lumen-core.ai/cohort/members/{slug}.html
Grants.gov: https://www.grants.gov/search-grants
OpenAI Responses: https://developers.openai.com/api/docs/guides/text
Coinbase public candles: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles

Software: MIT (LICENSE.txt). Third-party notices: THIRD_PARTY_NOTICES.txt.
Public descriptions do not transfer another business's name, brand or materials.
'''

def package(profile, source_files):
    contents=dict(source_files)
    contents['README.txt']=readme(profile).encode()
    contents['member-research.json']=(json.dumps(profile,ensure_ascii=False,indent=2)+'\n').encode()
    contents['public/cohort/catalog.json']=(json.dumps({'companies':[profile]},ensure_ascii=False,indent=2)+'\n').encode()
    # Preserve the existing software license without unrelated EIA data notices.
    license_text=(ROOT/'LICENSE').read_text(encoding='utf-8').split('Third-Party Data Notice')[0].strip()+'\n'
    contents['LICENSE.txt']=license_text.encode()
    contents['THIRD_PARTY_NOTICES.txt']=('three.js — Copyright © 2010-2026 three.js authors. MIT license.\nhttps://github.com/mrdoob/three.js/blob/dev/LICENSE\n\nPermission is hereby granted'+license_text.split('Permission is hereby granted',1)[1]+'\n\nFonts: DM Sans and Manrope are loaded from Google Fonts when online; system fonts are used offline. Font licenses are available from their Google Fonts project pages. No font files are redistributed.\n').encode()
    manifest={'schema':'lumencore.ec_member_package.v1','member':profile['id'],'files':[{'path':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()} for name,body in sorted(contents.items())],'private_data_included':False,'api_key_included':False,'live_orders_enabled':False}
    contents['package-manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,body in sorted(contents.items()):
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:raise ValueError('Unsafe package path')
            info=zipfile.ZipInfo(name,(2026,9,12,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,body,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    raw=buf.getvalue()
    if len(raw)>3_000_000:raise ValueError('Package exceeded the 3 MB bound')
    return raw

def build():
    catalog=json.loads((ROOT/'dashboard/cohort/catalog.json').read_text(encoding='utf-8'))
    if len(catalog['companies'])!=69:raise ValueError('Expected the complete official 69-member roster')
    source_files={}
    for name,source in FILES.items():
        path=ROOT/source
        if path.is_symlink() or not path.is_file():raise ValueError('Package source must be a regular file')
        body=path.read_bytes()
        if path.suffix in {'.py','.mjs','.js','.css','.html'}:body=body.replace(b'\r\n',b'\n')
        source_files[name]=body
    DEST.mkdir(parents=True,exist_ok=True)
    packages=[]
    for profile in catalog['companies']:
        body=package(profile,source_files)
        filename=profile['id']+'.zip'
        (DEST/filename).write_bytes(body)
        packages.append({'member':profile['id'],'file':filename,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
    manifest={'schema':'lumencore.ec_member_downloads.v1','source_catalog_sha256':hashlib.sha256((ROOT/'dashboard/cohort/catalog.json').read_bytes()).hexdigest(),'packages':packages}
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    return {'packages':len(packages),'total_bytes':sum(p['bytes'] for p in packages)}

if __name__=='__main__':print(json.dumps(build()))
