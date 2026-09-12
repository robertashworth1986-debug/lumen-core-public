#!/usr/bin/env python3
"""Build public member profiles from the already-reviewed, public research CSV.

This builder never reads private vaults, member email addresses, or credentials.
All observations remain hypotheses until members supply their own measurements.
"""
from __future__ import annotations
import csv
import hashlib
from html import escape
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs/EC_COHORT_STRENGTH_RESEARCH_2026-09-11.csv'
DEST = ROOT / 'dashboard/cohort/catalog.json'
ALIASES = {
    'govfetchrai-note-change-of-our-official-name-from-application': 'govfetchr-ai',
    'c3-community-partners-dao-llcmeasures-registry': 'c3-measures-registry',
    'proworx-blackhawk-catalyst-technology-consulting-llc': 'proworx',
    'music-utility-network-mun-a-venture-of-the-last-company': 'music-utility-network',
    'firma-consulting-group-dba-q-gaas': 'firma-q-gaas',
    'itty-bitty-city-at-project-reflect-inc': 'itty-bitty-city',
    'public-speaking-presentation-pros-academy': 'public-speaking-pros',
    'volume-one-nashville-vol1-nashville': 'volume-one-nashville',
}
WORKFLOWS = {
    'Manufacturing': ['Brief', 'Design', 'Approve', 'Produce', 'Accept'],
    'Healthcare': ['Request', 'Readiness', 'Match', 'Handoff', 'Confirm'],
    'Construction': ['Request', 'Survey', 'Quote', 'Schedule', 'Complete'],
    'Education': ['Discover', 'Enroll', 'Prepare', 'Learn', 'Follow up'],
    'Entertainment': ['Brief', 'Plan', 'Confirm', 'Deliver', 'Reconcile'],
    'Food and Beverage': ['Request', 'Plan', 'Prepare', 'Fulfill', 'Confirm'],
    'Retail': ['Discover', 'Select', 'Confirm', 'Fulfill', 'Follow up'],
    'IT / Technology': ['Request', 'Define', 'Review', 'Deliver', 'Verify'],
    'Real Estate': ['Inquiry', 'Qualify', 'Prepare', 'Review', 'Handoff'],
    'Transportation': ['Request', 'Plan', 'Confirm', 'Dispatch', 'Complete'],
    'Hospitality': ['Inquiry', 'Plan', 'Confirm', 'Host', 'Follow up'],
    'Financial Services': ['Inquiry', 'Scope', 'Review', 'Deliver', 'Reconcile'],
    'Social Enterprise / Nonprofit': ['Need', 'Plan', 'Resource', 'Deliver', 'Learn'],
}

PUBLIC_BASE = 'https://lumen-core.ai/cohort/'
PUBLIC_DATE = '2026-09-12'


def member_url(profile: dict) -> str:
    if not re.fullmatch(r'[a-z0-9-]{1,70}', profile['id']):
        raise ValueError('Unsafe member slug')
    return PUBLIC_BASE + 'members/' + profile['id'] + '.html'


def public_document(title: str, description: str, canonical: str, body: str, *, nested=False) -> str:
    asset = '../' if nested else './'
    metadata = json.dumps({
        '@context': 'https://schema.org', '@type': 'WebPage', 'name': title,
        'description': description, 'url': canonical,
        'isPartOf': {'@type': 'WebSite', 'name': 'EC Strength Studio', 'url': PUBLIC_BASE},
        'author': {'@type': 'Organization', 'name': 'LumenCore', 'url': 'https://lumen-core.ai/'},
    }, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description, quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#09111d">
<link rel="canonical" href="{escape(canonical, quote=True)}">
<meta property="og:type" content="website"><meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{escape(canonical, quote=True)}">
<meta property="og:image" content="https://lumen-core.ai/assets/lumaarc_arc_seal_v1.png">
<meta property="og:image:alt" content="LumenCore contribution to the TakeOff community">
<meta name="twitter:card" content="summary">
<link rel="icon" type="image/svg+xml" href="{asset}mark.svg"><link rel="stylesheet" href="{asset}studio.css">
<script type="application/ld+json">{metadata}</script>
</head><body class="public-profile">
<a class="skip" href="#main">Skip to profile</a>
<header class="profile-header"><a class="studio-brand" href="{asset}directory.html"><span class="brand-orbit" aria-hidden="true">L</span><span>STRENGTH<small>STUDIO / by LumenCore</small></span></a><a class="btn" href="{asset}directory.html">Meet the cohort ↗</a></header>
<main id="main" tabindex="-1">{body}</main>
<footer class="profile-footer"><strong>Our strength is making everyone else stronger.</strong><p>Independent LumenCore contribution. No EC or member endorsement implied. Public research reviewed September 2026.</p><a href="https://lumen-core.ai/proof_to_pilot.html">About LumenCore ↗</a></footer>
</body></html>
'''


def render_member_page(profile: dict) -> str:
    canonical = member_url(profile)
    name = escape(profile['name'])
    slug = profile['id']
    workspace = '../?member=' + slug
    questions = ''.join(f'''<article class="panel profile-question"><div class="panel-head"><span class="number">0{i+1}</span><span class="badge amber">OWNER INPUT NEEDED</span></div><div class="panel-body"><h3>{escape(h['question'])}</h3><p>{escape(h['contribution'])}</p><details><summary>What we could measure together</summary><p><strong>Measure:</strong> {escape(h['metric'])} ({escape(h['unit'])}).</p><p>{escape(h['measurement_plan'])}</p><p><strong>Acceptance boundary:</strong> {escape(h['boundary'])}</p></details></div></article>''' for i, h in enumerate(profile['hypotheses']))
    sources = ''.join(f'<li><a href="{escape(url, quote=True)}" rel="noopener noreferrer">{escape(url)}</a></li>' for url in profile['sources'] if safe_url(url))
    business = profile.get('official_site', '')
    business_link = f'<a class="btn" href="{escape(business, quote=True)}" rel="noopener noreferrer">Visit business source ↗</a>' if safe_url(business) else ''
    flow = ''.join(f'<li><span>0{i+1}</span>{escape(stage)}</li>' for i, stage in enumerate(profile['workflow']))
    body = f'''<section class="profile-intro"><span class="eyebrow">TAKEOFF FALL 2026 · {escape(profile['industry']).upper()}</span><h1>{name}</h1><p class="profile-strength">{escape(profile['strength'])}</p><div class="button-row"><a class="btn primary" href="{workspace}">Open {name} workspace ↗</a>{business_link}<a class="btn" href="../downloads/{slug}.zip">Download free package ↓</a></div><p class="profile-disclosure">A public strength profile and free toolkit from a fellow founder. This is an independent contribution, not a website operated by {name}.</p></section>
<section class="panel"><div class="panel-head"><h2>A possible path through the work</h2><span class="badge neutral">PROPOSED FLOW</span></div><div class="panel-body"><ol class="profile-flow">{flow}</ol><p class="muted small">These stages are a starting point for owner review. The interactive workspace includes a rotatable 3D view of this proposed flow.</p></div></section>
<section class="profile-section"><div class="panel-head"><h2>Three questions worth exploring</h2><span class="badge">PUBLIC RESEARCH</span></div><p class="muted">These are hypotheses to discuss, with current baselines unmeasured. They do not establish that a problem or loss occurs in this business.</p><div class="profile-questions">{questions}</div></section>
<section class="panel"><div class="panel-head"><h2>Your free Luma toolkit</h2><span class="badge">PORTABLE PACKAGE</span></div><div class="panel-body"><div class="profile-tool-grid"><div><h3>Make work easier to follow</h3><p>Use a workboard, acceptance criteria, revision fingerprints and measurement records to define the next useful step.</p></div><div><h3>Prepare and explore</h3><p>Grant Factory drafts from supplied facts, a public opportunity scout, and fictional-money paper trading tools are included.</p></div><div><h3>Coordinate and learn</h3><p>LumaCare supports nonclinical coordination practice. Optional AI drafting uses the member's own API account and credits.</p></div></div><div class="button-row"><a class="btn primary" href="{workspace}#package">Get your package and setup instructions</a><a class="btn" href="{workspace}#measure">Plan a measurement ↗</a></div><p class="profile-disclosure">The public workspace stores work in your browser. The downloaded Python app adds local backups and optional hourly public-source scout and paper jobs while it stays open. No shared team accounts, clinical deployment, grant submission or live trading are included.</p></div></section>
<section class="profile-section"><h2>Public sources and corrections</h2><p class="muted">The strength description and questions come from the reviewed public research below. Owner corrections and actual operating records should guide any next experiment.</p><ul class="profile-sources">{sources}</ul><a href="https://github.com/robertashworth1986-debug/lumen-core-public/blob/main/docs/EC_COHORT_STRENGTH_RESEARCH_2026-09-11.md">Read the complete cohort research ↗</a></section>'''
    return public_document(profile['name'] + ' · EC Strength Studio', profile['strength'], canonical, body, nested=True)


def render_public_directory(companies: list[dict]) -> str:
    cards = ''.join(f'''<article class="card"><span class="badge neutral">{escape(c['industry'])}</span><h2><a href="members/{c['id']}.html">{escape(c['name'])}</a></h2><p>{escape(c['strength'])}</p><a class="btn" href="members/{c['id']}.html">Explore strength profile ↗</a></article>''' for c in companies)
    body = f'''<section class="profile-intro"><span class="eyebrow">69 BUSINESSES · ONE COMMUNITY</span><h1>Discover the strength next door.</h1><p class="profile-strength">Meet the TakeOff Fall 2026 businesses through their publicly described strengths. Every profile includes three workflow questions, public sources and a free member toolkit.</p><a class="btn primary" href="./?member=excalis#directory">Search the interactive directory ↗</a><p class="profile-disclosure">Independent public-source research. The owners' workflows, baselines and results still need their input.</p></section><div class="card-grid">{cards}</div>'''
    return public_document('Meet the TakeOff businesses · EC Strength Studio', 'Discover 69 TakeOff businesses, their public strengths, three workflow questions each, and free member toolkits from LumenCore.', PUBLIC_BASE + 'directory.html', body)


def write_public_pages(companies: list[dict]) -> None:
    folder = DEST.parent / 'members'
    folder.mkdir(parents=True, exist_ok=True)
    for profile in companies:
        member_url(profile)
        page = render_member_page(profile)
        if len(page.encode()) > 50000:
            raise ValueError('Public member page exceeds the 50 KB bound')
        (folder / (profile['id'] + '.html')).write_text(page, encoding='utf-8', newline='\n')
    directory = render_public_directory(companies)
    if len(directory.encode()) > 400000:
        raise ValueError('Public directory exceeds the 400 KB bound')
    (DEST.parent / 'directory.html').write_text(directory, encoding='utf-8', newline='\n')
    sitemap = ROOT / 'dashboard/sitemap.xml'
    current = sitemap.read_text(encoding='utf-8')
    start, end = '<!-- EC STRENGTH PROFILES START -->', '<!-- EC STRENGTH PROFILES END -->'
    urls = [PUBLIC_BASE, PUBLIC_BASE + 'directory.html'] + [member_url(c) for c in companies]
    block = start + '\n' + ''.join(f'  <url><loc>{escape(url)}</loc><lastmod>{PUBLIC_DATE}</lastmod></url>\n' for url in urls) + '  ' + end
    if start in current:
        if current.count(start) != 1 or current.count(end) != 1:
            raise ValueError('Ambiguous cohort sitemap block')
        current = current[:current.index(start)] + block + current[current.index(end) + len(end):]
    else:
        if current.count('</urlset>') != 1:
            raise ValueError('Missing canonical sitemap end')
        current = current.replace('</urlset>', '  ' + block + '\n</urlset>')
    sitemap.write_text(current, encoding='utf-8', newline='\n')

def safe_url(value: str) -> bool:
    p = urlparse(value)
    return p.scheme in {'https', 'http'} and bool(p.hostname) and not p.username and not p.password

def build() -> dict:
    raw = SOURCE.read_bytes()
    # Git normalizes this source to LF. The receipt hashes canonical source bytes.
    source_bytes = raw.replace(b'\r\n', b'\n')
    grouped: dict[str, dict] = {}
    with SOURCE.open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            if row['status'] != 'HYPOTHESIS_REQUIRES_OWNER_VALIDATION':
                raise ValueError('Unexpected research evidence status')
            original = row['company_id']
            if original not in grouped:
                slug = ALIASES.get(original, unicodedata.normalize('NFKD', original).encode('ascii', 'ignore').decode())
                if not re.fullmatch(r'[a-z0-9-]{1,70}', slug):
                    raise ValueError('Unsafe member slug')
                grouped[original] = {
                    'id': slug, 'research_id': original, 'name': row['company'],
                    'industry': row['industry'], 'strength': row['public_strength'],
                    'workflow': WORKFLOWS.get(row['industry'], ['Inquiry', 'Scope', 'Prepare', 'Deliver', 'Follow up']),
                    'hypotheses': [], 'sources': [], 'official_site': '',
                    'owner_confirmed': False,
                }
            company = grouped[original]
            sources = [x.strip() for x in row['sources'].split(' | ') if safe_url(x.strip())]
            for url in sources:
                if url not in company['sources']:
                    company['sources'].append(url)
                if not company['official_site'] and urlparse(url).hostname not in {'ec.co', 'www.ec.co'}:
                    company['official_site'] = url
            company['hypotheses'].append({
                'id': row['hypothesis_id'], 'question': row['question'],
                'metric': row['baseline_metric'], 'unit': row['unit'],
                'measurement_plan': row['measurement_plan'], 'formula': row['formula'],
                'secondary_measurements': row['secondary_measurements'],
                'contribution': row['possible_contribution'], 'boundary': row['acceptance_boundary'],
                'observed_value': None,
            })
    if len(grouped) != 69 or any(len(c['hypotheses']) != 3 for c in grouped.values()):
        raise ValueError('Expected exactly 69 cohort members and three hypotheses each')
    if len({c['id'] for c in grouped.values()}) != 69:
        raise ValueError('Member slug collision')
    payload = {
        'schema': 'lumencore.ec_strength_studio.catalog.v1',
        'slogan': 'Our strength is making everyone else stronger.',
        'research_date': '2026-09-11', 'source': SOURCE.relative_to(ROOT).as_posix(),
        'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'evidence_boundary': 'Public-source hypotheses. Owner baselines, endorsements and achieved savings are not established.',
        'companies': list(grouped.values()),
    }
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    write_public_pages(payload['companies'])
    return {'companies': len(grouped), 'hypotheses': sum(len(c['hypotheses']) for c in grouped.values()), 'source_sha256': payload['source_sha256'], 'public_member_pages': len(grouped)}

if __name__ == '__main__':
    print(json.dumps(build()))
