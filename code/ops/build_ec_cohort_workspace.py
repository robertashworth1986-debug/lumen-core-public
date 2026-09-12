#!/usr/bin/env python3
"""Build public member profiles from the already-reviewed, public research CSV.

This builder never reads private vaults, member email addresses, or credentials.
All observations remain hypotheses until members supply their own measurements.
"""
from __future__ import annotations
import csv
import hashlib
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
    return {'companies': len(grouped), 'hypotheses': sum(len(c['hypotheses']) for c in grouped.values()), 'source_sha256': payload['source_sha256']}

if __name__ == '__main__':
    print(json.dumps(build()))
