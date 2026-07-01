from __future__ import annotations

import hashlib
import json
import ssl
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

LIVE_DOMAIN_FEED = OUT_OPS / "live_domain_deployment_feed_latest.json"
CHAMPION_BRIDGE = OUT_OPS / "champion_sample_expansion_and_economic_bridge_latest.json"

OUT_JSON = OUT_OPS / "live_domain_consolidation_audit_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "live_domain_consolidation_audit.json"
OUT_MD = DOCS / "LIVE_DOMAIN_CONSOLIDATION_AUDIT_2026-06-30.md"

BASE_URL = "https://lumen-core.ai/"
MAX_URLS = 80

BOUNDARY = (
    "Live-domain consolidation audit. This artifact reports what the public site appears to expose, "
    "which pages should remain reviewer-facing, which surfaces should be demoted, and whether hosted proof feeds "
    "hash-match the local proof stack. It does not claim field validation, realized savings, guaranteed funding, "
    "fixed frozen-delta pricing, live trading performance, medical efficacy, or buyer acceptance."
)

PUBLIC_CORE_SURFACES = [
    {
        "url": "https://lumen-core.ai/",
        "role": "front_door",
        "decision": "keep_and_tighten",
        "why": "Best public entry point, but it must route viewers to proof rather than hype.",
    },
    {
        "url": "https://lumen-core.ai/mission_control.html",
        "role": "executive_operator_board",
        "decision": "keep_as_primary",
        "why": "Best all-up command view if it shows claim gates, freshness, and blockers clearly.",
    },
    {
        "url": "https://lumen-core.ai/quant_lab.html",
        "role": "technical_evidence_board",
        "decision": "keep_as_primary",
        "why": "Best home for live-breadth replay, geometry families, baselines, and uncertainty.",
    },
    {
        "url": "https://lumen-core.ai/grants.html",
        "role": "funding_submission_board",
        "decision": "keep_as_primary",
        "why": "Best home for grant readiness, submission kits, and reviewer-safe proposal state.",
    },
    {
        "url": "https://lumen-core.ai/evidence/",
        "role": "proof_ledger",
        "decision": "keep_but_rename_tone",
        "why": "Evidence ledger is important; title should read credible and auditable, not overconfident.",
    },
]

PUBLIC_DEMOTE_RULES = {
    "kraken": "Keep as paper/research sandbox. Do not present as institutional trading performance.",
    "lumascout": "Keep optional, but not part of the energy/grant proof funnel.",
    "agent_approval": "Internal operator control surface, not public reviewer evidence.",
    "forecast": "Internal demo unless tied to locked baselines and held-out external data.",
}

RISK_TERMS = [
    "guaranteed",
    "money printer",
    "realized",
    "profit",
    "billion",
    "undeniable",
    "field validated",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: v for k, v in attrs if v}
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "link" and values.get("href"):
            self.links.append(values["href"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        self.text_parts.append(text)
        if self._in_title:
            self.title_parts.append(text)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_url(url: str) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    request = urllib.request.Request(url, headers={"User-Agent": "LumaDomainConsolidationAudit/1.0"})
    try:
        with urllib.request.urlopen(request, context=ctx, timeout=15) as response:
            body = response.read(2_000_000)
            return {
                "ok": True,
                "status": response.status,
                "url": response.geturl(),
                "content_type": response.headers.get("content-type", ""),
                "bytes": len(body),
                "body": body,
                "error": "",
            }
    except Exception as exc:  # pragma: no cover - network state is expected to vary.
        return {
            "ok": False,
            "status": None,
            "url": url,
            "content_type": "",
            "bytes": 0,
            "body": b"",
            "error": str(exc)[:300],
        }


def same_domain(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc in {"lumen-core.ai", "www.lumen-core.ai"}


def normalize_url(base_url: str, href: str) -> str:
    absolute = urllib.parse.urljoin(base_url, href)
    parsed = urllib.parse.urlparse(absolute)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def crawl_domain() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queue: deque[str] = deque([BASE_URL])
    seen: set[str] = set()
    pages: list[dict[str, Any]] = []
    linked_assets: list[dict[str, Any]] = []

    while queue and len(seen) < MAX_URLS:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        result = fetch_url(url)
        body = result.pop("body")
        path = urllib.parse.urlparse(result["url"]).path

        if result["ok"] and "text/html" in result["content_type"]:
            html = body.decode("utf-8", "replace")
            parser = LinkParser()
            parser.feed(html)
            page_text = " ".join(parser.text_parts)
            risk_terms = [term for term in RISK_TERMS if term.lower() in page_text.lower()]
            pages.append(
                {
                    **result,
                    "title": " ".join(parser.title_parts),
                    "links_count": len(parser.links),
                    "scripts_count": len(parser.scripts),
                    "risk_terms_seen": risk_terms,
                    "snippet": page_text[:600],
                }
            )
            for href in parser.links + parser.scripts:
                candidate = normalize_url(result["url"], href)
                if same_domain(candidate) and candidate not in seen and len(seen) + len(queue) < MAX_URLS:
                    queue.append(candidate)
        else:
            linked_assets.append(result)

    return pages, linked_assets


def classify_public_pages(pages: list[dict[str, Any]], assets: list[dict[str, Any]]) -> dict[str, Any]:
    page_urls = {row["url"]: row for row in pages}
    broken = [row for row in assets if not row["ok"] and same_domain(row["url"])]
    demote: list[dict[str, Any]] = []
    for row in pages:
        key = row["url"].lower()
        reason = ""
        for needle, explanation in PUBLIC_DEMOTE_RULES.items():
            if needle in key or needle in row.get("title", "").lower():
                reason = explanation
                break
        if reason:
            demote.append({"url": row["url"], "title": row.get("title", ""), "reason": reason})

    missing_core = [surface for surface in PUBLIC_CORE_SURFACES if surface["url"] not in page_urls]
    risk_pages = [
        {"url": row["url"], "title": row.get("title", ""), "risk_terms_seen": row["risk_terms_seen"]}
        for row in pages
        if row.get("risk_terms_seen")
    ]
    return {
        "core_surfaces": PUBLIC_CORE_SURFACES,
        "missing_core_surfaces": missing_core,
        "demote_or_internalize": demote,
        "broken_internal_links": [
            {"url": row["url"], "status": row.get("status"), "error": row.get("error", "")} for row in broken
        ],
        "risk_language_review": risk_pages,
    }


def build_payload() -> dict[str, Any]:
    pages, assets = crawl_domain()
    live_feed = read_json(LIVE_DOMAIN_FEED)
    bridge = read_json(CHAMPION_BRIDGE)
    live_summary = live_feed.get("summary", {})
    bridge_summary = bridge.get("summary", {})

    stale_required = [row.get("key") for row in live_feed.get("required_remote_missing_or_stale", [])]
    classification = classify_public_pages(pages, assets)
    public_ready = bool(live_summary.get("live_domain_reviewer_ready"))

    summary = {
        "public_domain_up": any(row["ok"] and row["url"].rstrip("/") == BASE_URL.rstrip("/") for row in pages),
        "page_count": len(pages),
        "linked_asset_or_error_count": len(assets),
        "core_surface_count": len(PUBLIC_CORE_SURFACES),
        "broken_internal_link_count": len(classification["broken_internal_links"]),
        "risk_language_page_count": len(classification["risk_language_review"]),
        "local_required_ready": bool(live_summary.get("local_required_ready")),
        "live_domain_reviewer_ready": public_ready,
        "required_feed_count": live_summary.get("required_feed_count", 0),
        "required_remote_hash_match_count": live_summary.get("required_remote_hash_match_count", 0),
        "required_remote_reachable_count": live_summary.get("required_remote_reachable_count", 0),
        "stale_required_feed_count": len(stale_required),
        "stale_required_feeds": stale_required,
        "wave_resonance_win_rate": bridge_summary.get("wave_resonance_win_rate"),
        "estimated_rows_replayed": bridge_summary.get("estimated_rows_replayed"),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_frozen_delta_price_claim_allowed": False,
        "plain_english_answer": (
            "The live domain is online and visually strong, but it should not be treated as reviewer-ready until "
            "the required proof feeds hash-match the local proof stack and risky public language is tightened."
        ),
    }

    payload = {
        "schema": "live_domain_consolidation_audit_v1",
        "generated_utc": utc_now(),
        "boundary": BOUNDARY,
        "summary": summary,
        "public_pages": pages,
        "linked_assets": assets,
        "classification": classification,
        "recommended_master_board_model": [
            "Public front door: /",
            "Executive command: /mission_control.html",
            "Technical evidence: /quant_lab.html",
            "Funding/submissions: /grants.html",
            "Evidence ledger nested under command/proof: /evidence/",
        ],
        "immediate_cleanup_actions": [
            "Push and verify stale required feeds on lumen-core.ai/data before sending reviewers.",
            "Rename or soften overconfident public labels such as 'Undeniable Evidence' to 'Evidence Ledger'.",
            "Remove public-facing dollar/profit/guarantee wording unless the artifact explicitly labels it as illustrative.",
            "Demote Kraken, LumaScout, agent approval, and generic forecast pages from the primary reviewer path.",
            "Make the 600/600 wave-resonance result a technical proof card with the exact boundary: internal source-conditioned replay, not field validation.",
            "Route EPRI, Spark/TVA/UT, and TAEBC visitors to a clean pilot-validation request rather than a broad platform tour.",
        ],
        "who_should_see_it_after_cleanup": [
            "EPRI Incubatenergy Labs or utility innovation teams",
            "Spark Innovation Center / TVA / UT Research Park mentors",
            "Tennessee Advanced Energy Business Council warm-intro partners",
            "DOE/DARPA/SBIR reviewers when tied to a specific solicitation and claim gate",
            "Datacenter energy/cooling operators after thermal samples expand",
        ],
    }
    payload["audit_sha256"] = sha256_text(json.dumps(payload, sort_keys=True, default=str))
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    c = payload["classification"]
    lines = [
        "# Live Domain Consolidation Audit",
        "",
        f"Generated: {payload['generated_utc']}",
        "",
        "## Boundary",
        "",
        payload["boundary"],
        "",
        "## Current Public State",
        "",
        f"- Public domain up: `{s['public_domain_up']}`",
        f"- Pages observed: `{s['page_count']}`",
        f"- Core reviewer surfaces: `{s['core_surface_count']}`",
        f"- Live-domain reviewer ready: `{s['live_domain_reviewer_ready']}`",
        f"- Local required feeds ready: `{s['local_required_ready']}`",
        f"- Required feed hash matches: `{s['required_remote_hash_match_count']}` / `{s['required_feed_count']}`",
        f"- Required feeds reachable: `{s['required_remote_reachable_count']}` / `{s['required_feed_count']}`",
        f"- Stale required feeds: `{s['stale_required_feed_count']}`",
        f"- Broken internal links observed: `{s['broken_internal_link_count']}`",
        f"- Pages needing claim-language review: `{s['risk_language_page_count']}`",
        f"- Wave resonance win rate: `{s['wave_resonance_win_rate']}`",
        f"- Estimated rows replayed: `{s['estimated_rows_replayed']}`",
        f"- Field-validation claim allowed: `{s['field_validation_claim_allowed']}`",
        f"- Real-dollar savings claim allowed: `{s['real_dollar_savings_claim_allowed']}`",
        "",
        "## Plain English",
        "",
        s["plain_english_answer"],
        "",
        "## Keep As Master Surfaces",
        "",
    ]
    for surface in c["core_surfaces"]:
        lines.append(f"- `{surface['url']}`: {surface['decision']} - {surface['why']}")

    if c["demote_or_internalize"]:
        lines += ["", "## Demote Or Internalize", ""]
        for row in c["demote_or_internalize"]:
            lines.append(f"- `{row['url']}` ({row['title']}): {row['reason']}")

    if c["broken_internal_links"]:
        lines += ["", "## Broken Internal Links", ""]
        for row in c["broken_internal_links"]:
            lines.append(f"- `{row['url']}`: {row['error'] or row['status']}")

    if c["risk_language_review"]:
        lines += ["", "## Claim-Language Review Needed", ""]
        for row in c["risk_language_review"]:
            terms = ", ".join(f"`{term}`" for term in row["risk_terms_seen"])
            lines.append(f"- `{row['url']}` ({row['title']}): {terms}")

    lines += [
        "",
        "## Stale Required Feeds",
        "",
    ]
    if s["stale_required_feeds"]:
        for key in s["stale_required_feeds"]:
            lines.append(f"- `{key}`")
    else:
        lines.append("- none")

    lines += [
        "",
        "## Immediate Cleanup Actions",
        "",
    ]
    for action in payload["immediate_cleanup_actions"]:
        lines.append(f"- {action}")

    lines += [
        "",
        "## Who Should See It After Cleanup",
        "",
    ]
    for target in payload["who_should_see_it_after_cleanup"]:
        lines.append(f"- {target}")

    lines += [
        "",
        "## Audit Hash",
        "",
        f"`{payload['audit_sha256']}`",
        "",
    ]
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_OPS.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    OUT_JSON.write_text(text, encoding="utf-8")
    DASHBOARD_JSON.write_text(text, encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def main() -> None:
    payload = build_payload()
    write_outputs(payload)
    s = payload["summary"]
    print(
        "Built live-domain consolidation audit: "
        f"pages={s['page_count']} reviewer_ready={s['live_domain_reviewer_ready']} "
        f"hashes={s['required_remote_hash_match_count']}/{s['required_feed_count']} "
        f"broken={s['broken_internal_link_count']} sha256={payload['audit_sha256'][:12]}"
    )


if __name__ == "__main__":
    main()
