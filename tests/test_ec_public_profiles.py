"""Public member discovery must work in the returned HTML without JavaScript."""
from __future__ import annotations

from copy import deepcopy
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'dashboard/cohort/catalog.json').read_text(encoding='utf-8'))


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load('code/ops/build_ec_cohort_workspace.py', 'ec_profile_builder')
PACKAGER = load('code/deploy/package_public_site_release.py', 'ec_profile_release')


class Page(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.words = []
        self.feed(raw)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.words.append(data)

    def values(self, tag, attr, **where):
        return [a.get(attr) for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in where.items())]


def test_all_members_have_unique_complete_public_html_and_canonical_metadata():
    expected = {c['id'] + '.html' for c in CATALOG['companies']}
    folder = ROOT / 'dashboard/cohort/members'
    assert {p.name for p in folder.glob('*.html')} == expected
    titles = set()
    for c in CATALOG['companies']:
        raw = (folder / (c['id'] + '.html')).read_text(encoding='utf-8')
        assert raw == BUILDER.render_member_page(c)
        assert len(raw.encode()) < 50000
        page = Page(raw)
        canonical = BUILDER.member_url(c)
        assert page.values('link', 'href', rel='canonical') == [canonical]
        assert page.values('meta', 'content', property='og:url') == [canonical]
        title = c['name'] + ' · EC Strength Studio'
        assert title in page.words
        titles.add(title)
        for text in [c['name'], c['strength'], *[h['question'] for h in c['hypotheses']]]:
            assert text in page.words
        assert page.values('script', 'type') == ['application/ld+json']
        assert page.values('script', 'src') == [None]
        assert 'current baselines unmeasured' in ' '.join(page.words)
        for source in c['sources']:
            assert source in page.values('a', 'href')
    assert len(titles) == 69


def test_public_pages_have_dependency_complete_links_in_the_exact_release():
    allowed = set(PACKAGER.RELEASE_PATHS)
    paths = ['dashboard/cohort/directory.html'] + ['dashboard/cohort/members/' + c['id'] + '.html' for c in CATALOG['companies']]
    for relative in paths:
        assert relative in allowed
        page = Page((ROOT / relative).read_text(encoding='utf-8'))
        base = 'https://lumen-core.ai/' + relative.removeprefix('dashboard/')
        for tag, attrs in page.tags:
            if tag not in {'a', 'link'} or 'href' not in attrs:
                continue
            url = urlparse(urljoin(base, attrs['href']))
            if url.netloc != 'lumen-core.ai':
                continue
            path = url.path
            path = path + 'index.html' if path.endswith('/') else path
            if path == '/index.html':
                path = '/operator_home.html'
            assert 'dashboard' + path in allowed, (relative, path)


def test_directory_and_sitemap_expose_every_member_without_scripts():
    page = Page((ROOT / 'dashboard/cohort/directory.html').read_text(encoding='utf-8'))
    links = {urljoin(BUILDER.PUBLIC_BASE + 'directory.html', x) for x in page.values('a', 'href')}
    expected = {BUILDER.member_url(c) for c in CATALOG['companies']}
    assert expected <= links
    root = ET.parse(ROOT / 'dashboard/sitemap.xml').getroot()
    locations = [e.text for e in root.findall('{*}url/{*}loc')]
    assert len(locations) == len(set(locations))
    assert expected | {BUILDER.PUBLIC_BASE, BUILDER.PUBLIC_BASE + 'directory.html'} <= set(locations)
    assert 'Disallow: /cohort' not in (ROOT / 'dashboard/robots.txt').read_text()


def test_profile_escaping_and_path_bounds_preserve_inert_public_research():
    c = deepcopy(CATALOG['companies'][0])
    c['name'] = '</title><script>alert(1)</script>'
    c['strength'] = '</script><img src=x onerror=alert(1)>'
    c['sources'] = ['javascript:alert(1)', 'https://example.com/?a=1&b=2']
    c['official_site'] = 'javascript:alert(1)'
    page = Page(BUILDER.render_member_page(c))
    assert page.values('script', 'type') == ['application/ld+json']
    assert not any(t == 'img' for t, _ in page.tags)
    assert not any((href or '').startswith('javascript:') for href in page.values('a', 'href'))
    c['id'] = '../outside'
    with pytest.raises(ValueError, match='slug'):
        BUILDER.render_member_page(c)
