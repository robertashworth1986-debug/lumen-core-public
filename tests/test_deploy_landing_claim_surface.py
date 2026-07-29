from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "deploy" / "landing" / "index.html"


def landing_text() -> str:
    return LANDING.read_text(encoding="utf-8")


def test_deployable_landing_page_has_no_unsupported_execution_claims_or_ids():
    text = landing_text()
    lowered = text.lower()

    prohibited = {
        "institutional-grade",
        "live exchange execution",
        "live execution proven",
        "verifiable kraken txids",
        "kraken txids",
        "real pnl ledger",
        "paper-trading screenshot factory",
    }
    assert not any(value in lowered for value in prohibited)
    assert re.search(r"\bO[A-Z0-9]{5,}(?:-[A-Z0-9]{5,}){2}\b", text) is None


def test_deployable_landing_page_states_current_evidence_boundaries():
    lowered = landing_text().lower()

    assert "no performance champion" in lowered
    assert "paper/replay-only" in lowered
    assert "hash proves identity, not model skill" in lowered
    assert "explicit human action" in lowered
    assert "no alpha, field-performance, or savings claim" in lowered
    assert "140 registered families" in lowered
    assert "126 direct source-baseline comparisons" in lowered


def test_landing_structured_data_is_valid_and_uses_safe_positioning():
    text = landing_text()
    match = re.search(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    payload = json.loads(match.group(1))
    dumped = json.dumps(payload).lower()

    assert payload["@context"] == "https://schema.org"
    assert "evidence-governed" in dumped
    assert "live exchange" not in dumped
    assert "institutional-grade" not in dumped


def test_landing_internal_evidence_links_resolve_in_the_repository():
    text = landing_text()
    links = set(re.findall(r'href="(/(?:dashboard|out)/[^"]+)"', text))

    assert links
    for link in links:
        assert (ROOT / link.lstrip("/")).is_file(), link
