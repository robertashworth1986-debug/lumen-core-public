"""Legacy routes expose dated evidence while preserving the public boundary."""
from pathlib import Path
from html.parser import HTMLParser
import importlib.util
import json
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('research_views', ROOT/'code/ops/build_research_review_surfaces.py')
views = importlib.util.module_from_spec(spec)
spec.loader.exec_module(views)

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set()
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f"duplicate id {attrs['id']}"
            self.ids.add(attrs['id'])
        if tag=='a' and 'href' in attrs: self.links.append(attrs['href'])

def test_research_routes_preserve_public_boundary_and_evidence():
    for route in views.PAGES:
        text=(ROOT/'dashboard'/route).read_text()
        assert text == views.render_page(ROOT,route), f"stale generated page: {route}"
        for required in ('research-review-v2','noindex,nofollow,noarchive','HOLD','production readiness','field validation','DATED EVIDENCE'):
            assert required in text
        for forbidden in ('/api/snapshot','/api/events/recent','location.replace','http-equiv="refresh"','Authorization:','api_key','onclick='):
            assert forbidden not in text
        parser=Links();parser.feed(text)
        for target in views.PAGES:
            assert '/'+target in parser.links
        assert '/proof_to_pilot.html' in parser.links
        assert '/cohort/' in parser.links

def test_kraken_preserves_order_ids_and_follow_on_losses():
    text=(ROOT/'dashboard/kraken_execution_dashboard.html').read_text()
    assert 'OB2KD6-VTJPR-T4MGLO' in text
    assert 'order-to-fill and fee reconciliation remains open' in text
    assert '-2.145' in text and '5.700' in text
    assert 'approved zero' in text
    assert 'not a verified live-account return' in text

def test_shared_navigation_never_fetches_operator_snapshot():
    text=(ROOT/'dashboard/assets/luma_command_fabric.js').read_text()
    start=text.index('function updateStatus()')
    end=text.index('function buildRail()',start)
    assert 'return updatePublicStatus();' in text[start:end]
    assert 'updateOperatorStatus' not in text[start:end]

def test_changed_inputs_cannot_keep_frozen_source_citations():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);path=root/'investor_txids/trade_log.json'
        path.parent.mkdir(parents=True)
        data=json.loads((ROOT/'investor_txids/trade_log.json').read_text())
        data[0]['pnl']=999999
        path.write_text(json.dumps(data))
        try:
            views.read(root,'investor_txids/trade_log.json')
        except ValueError as error:
            assert 'Evidence changed' in str(error)
        else:
            raise AssertionError('Mutated evidence accepted under a frozen citation')
