"""Federal opportunity harvester.

Pulls grant/contract opportunities from public federal APIs and scores them
against the company profile in `data/company_profile.json`.

Sources (all free / public):
  * Grants.gov Search2 API   - https://api.grants.gov/v1/api/search2  (no key)
  * SBIR.gov solicitations   - https://api.www.sbir.gov/public/api/solicitations  (no key)
    * SAM.gov Opportunities    - https://api.sam.gov/opportunities/v2/search
                                                                (key OPTIONAL via env SAM_API_KEY or SAM_GOV_API_KEY)
  * SBA loan programs        - static catalog (no public opportunity API)

Output:
  out/opportunities/harvest_<UTC>.json   -- raw fetched records
  out/opportunities/ranked.json          -- scored + filtered "perfect-fit" set
  out/opportunities/queue.jsonl          -- approval queue (one record per line)

Run:
  python code/opportunity_harvester.py [--limit 1000] [--min-score 0.45]

Honest constraints:
  * Federal grant/contract submission requires HUMAN login + e-sign.
    This harvester drafts a pre-filled package and queues it; it never
    auto-submits to grants.gov / sam.gov / agency portals.
  * SBA loans are not API-applyable; bank-mediated. We surface program
    details only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "out" / "opportunities"
OUT.mkdir(parents=True, exist_ok=True)

KNOWN_ENV_FILES = [
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
]

PROFILE_PATH = DATA / "company_profile.json"
CATALOG_PATH = DATA / "grant_catalog.json"

# Profile keyword pool (built once from profile + catalog) drives fit scoring.
DEFAULT_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "ml", "forecasting",
    "anomaly detection", "regime", "harmonic", "phase-locked", "calibration",
    "uncertainty", "time series", "deep tech", "infrastructure",
    "energy", "grid", "electricity", "weather", "climate", "earth observation",
    "data analytics", "decision support", "real-time", "explainable",
    "small business", "sbir", "sttr", "phase i", "phase ii",
    "operational", "scada", "resilience", "early warning", "novel algorithm",
    "evidence", "reproducibility", "benchmark",
]

# NAICS codes plausibly applicable to LumenCore / sole-prop deep-tech AI.
PROFILE_NAICS = [
    "541511",  # Custom Computer Programming Services
    "541512",  # Computer Systems Design Services
    "541690",  # Other Scientific & Technical Consulting
    "541714",  # Research & Development - Biotech / Physical / Engineering
    "541715",  # R&D - Physical, Engineering, Life Sciences
    "518210",  # Data Processing, Hosting
]


# --------------------------- HTTP helpers --------------------------------- #


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        value = v.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def _hydrate_known_env_files() -> None:
    for env_file in KNOWN_ENV_FILES:
        _load_env_file(env_file)


def _first_nonempty_env(*names: str) -> tuple[str | None, str | None]:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return name, value
    return None, None


def _http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict | None = None,
    timeout: float = 20.0,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    h = {"User-Agent": "LumenCore-Opportunity-Harvester/1.0",
         "Accept": "application/json"}
    if payload is not None:
        h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


# --------------------------- Sources -------------------------------------- #


def fetch_grants_gov(rows: int = 200, keywords: list[str] | None = None) -> list[dict]:
    """Grants.gov Search2 API. No key. Pagination via startRecordNum."""
    keywords = keywords or ["small business", "sbir", "ai", "data", "energy"]
    out: list[dict] = []
    seen: set[str] = set()
    for kw in keywords:
        try:
            payload = {
                "rows": rows,
                "keyword": kw,
                "oppStatuses": "forecasted|posted",
            }
            resp = _http_json(
                "https://api.grants.gov/v1/api/search2",
                method="POST",
                payload=payload,
            )
            hits = (resp.get("data", {}) or {}).get("oppHits", []) or []
            for h in hits:
                oid = str(h.get("id") or h.get("number") or "")
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                out.append({
                    "source": "grants.gov",
                    "id": oid,
                    "number": h.get("number"),
                    "title": h.get("title"),
                    "agency": h.get("agency") or h.get("agencyCode"),
                    "status": h.get("oppStatus"),
                    "open_date": h.get("openDate"),
                    "close_date": h.get("closeDate"),
                    "doc_type": h.get("docType"),
                    "url": f"https://www.grants.gov/search-results-detail/{oid}",
                    "raw": h,
                })
        except Exception as e:  # noqa: BLE001
            print(f"[grants.gov] keyword={kw!r} error: {e}")
    return out


def fetch_sbir_gov(keywords: list[str] | None = None) -> list[dict]:
    """SBIR.gov public solicitations. No key. Throttled to avoid 429s."""
    keywords = keywords or ["ai", "data", "forecasting", "energy", "grid"]
    out: list[dict] = []
    seen: set[str] = set()
    for kw in keywords:
        try:
            url = (
                "https://api.www.sbir.gov/public/api/solicitations?keyword="
                + urllib.parse.quote(kw)
            )
            resp = _http_json(url)
            items = resp if isinstance(resp, list) else resp.get("results", [])
            for s in items or []:
                oid = str(s.get("solicitation_number") or s.get("solicitation_id") or s.get("id") or "")
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                out.append({
                    "source": "sbir.gov",
                    "id": oid,
                    "title": s.get("solicitation_title") or s.get("title"),
                    "agency": s.get("agency"),
                    "status": s.get("current_status") or s.get("status"),
                    "open_date": s.get("open_date"),
                    "close_date": s.get("close_date"),
                    "doc_type": "SBIR/STTR",
                    "url": s.get("solicitation_link") or s.get("url"),
                    "topics": s.get("topics") or [],
                    "raw": s,
                })
        except Exception as e:  # noqa: BLE001
            print(f"[sbir.gov] keyword={kw!r} error: {e}")
        time.sleep(2.0)  # gentle pacing to avoid 429
    return out


def enrich_grants_gov_synopsis(records: list[dict], top_n: int = 100) -> int:
    """Fetch full opportunity detail for top_n grants.gov records to enable
    body-text scoring. Returns number enriched."""
    enriched = 0
    for rec in records[:top_n]:
        if rec.get("source") != "grants.gov":
            continue
        oid = rec.get("id")
        if not oid:
            continue
        try:
            resp = _http_json(
                "https://api.grants.gov/v1/api/fetchOpportunity",
                method="POST",
                payload={"opportunityId": int(oid)},
                timeout=15.0,
            )
            data = resp.get("data", {}) or {}
            syn = data.get("synopsis", {}) or {}
            rec.setdefault("raw", {})["synopsis"] = syn.get("synopsisDesc") or ""
            rec["raw"]["awardCeiling"] = syn.get("awardCeiling")
            rec["raw"]["awardFloor"] = syn.get("awardFloor")
            rec["raw"]["expectedAwards"] = syn.get("numberOfAwards")
            enriched += 1
        except Exception as e:  # noqa: BLE001
            print(f"[grants.gov detail] id={oid} error: {e}")
        time.sleep(0.3)
    return enriched


def fetch_sam_gov(api_key: str | None, *, days: int = 60, limit: int = 200) -> list[dict]:
    """SAM.gov Opportunities API. Requires api_key (you can request one
    from your active SAM.gov registration). Returns [] if no key."""
    if not api_key:
        return []
    end = datetime.now(timezone.utc).strftime("%m/%d/%Y")
    start_dt = datetime.now(timezone.utc).timestamp() - days * 86400
    start = datetime.fromtimestamp(start_dt, timezone.utc).strftime("%m/%d/%Y")
    out: list[dict] = []
    for naics in PROFILE_NAICS:
        try:
            qs = urllib.parse.urlencode({
                "api_key": api_key,
                "limit": min(limit, 1000),
                "postedFrom": start,
                "postedTo": end,
                "ncode": naics,
                "ptype": "p,o,k,r",  # presolicit, solicitation, combined, sources sought
            })
            url = f"https://api.sam.gov/opportunities/v2/search?{qs}"
            resp = _http_json(url)
            for o in resp.get("opportunitiesData", []) or []:
                out.append({
                    "source": "sam.gov",
                    "id": o.get("noticeId"),
                    "title": o.get("title"),
                    "agency": o.get("fullParentPathName"),
                    "status": o.get("type"),
                    "open_date": o.get("postedDate"),
                    "close_date": o.get("responseDeadLine"),
                    "doc_type": o.get("type"),
                    "url": o.get("uiLink"),
                    "naics": naics,
                    "raw": o,
                })
        except Exception as e:  # noqa: BLE001
            print(f"[sam.gov] naics={naics} error: {e}")
    return out


# --------------------------- Scoring --------------------------------------- #


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def score_fit(rec: dict, keywords: list[str]) -> tuple[float, list[str]]:
    blob_parts: list[str] = []
    for k in ("title", "agency", "doc_type", "status"):
        v = rec.get(k)
        if v:
            blob_parts.append(str(v))
    raw = rec.get("raw") or {}
    for k in ("description", "synopsis", "topic_description", "subject"):
        v = raw.get(k)
        if v:
            blob_parts.append(str(v))
    for t in rec.get("topics") or []:
        if isinstance(t, dict):
            blob_parts.append(str(t.get("topic_title") or t.get("title") or ""))
            blob_parts.append(str(t.get("topic_description") or ""))
        else:
            blob_parts.append(str(t))
    blob = _normalize(" ".join(blob_parts))

    matches: list[str] = []
    score = 0.0
    for kw in keywords:
        kwn = _normalize(kw)
        if not kwn:
            continue
        if kwn in blob:
            matches.append(kw)
            # Multi-word keywords weighted higher
            score += 1.5 if " " in kwn else 1.0

    # Eligibility bumps for sole-prop / small-business friendly programs
    if re.search(r"\bsbir|sttr|small\s+business\b", blob):
        score += 3.0
    if "phase i" in blob:
        score += 1.5
    if "rolling" in blob or "open topic" in blob:
        score += 1.0

    # Normalize to 0..1 against rough ceiling
    # (titles alone rarely score above 6; full synopses can hit 12+)
    norm = min(1.0, score / 6.0)
    return norm, matches


def is_actionable(rec: dict) -> bool:
    """Filter out closed / archived / unfundable rows + agency noise."""
    status = _normalize(str(rec.get("status") or ""))
    if status in {"closed", "archived", "cancelled", "canceled"}:
        return False

    # Profile exclusion: State Dept missions, PEPFAR, narrow-foreign,
    # K-12 education — high keyword overlap, zero fit for solo-prop AI.
    agency = _normalize(str(rec.get("agency") or ""))
    title = _normalize(str(rec.get("title") or ""))
    EXCLUDE_AGENCY = (
        "u.s. mission", "u.s.embassy", "embassy ", "consulate",
        "pepfar", "peace corps", "fulbright",
        "office of overseas schools",
    )
    if any(x in agency for x in EXCLUDE_AGENCY):
        return False
    EXCLUDE_TITLE = (
        "alumni engagement", "freedom 250", "youth ambassador",
        "k-12", "fulbright",
    )
    if any(x in title for x in EXCLUDE_TITLE):
        return False

    cd = rec.get("close_date")
    if cd:
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                dt = datetime.strptime(cd[:19] if "T" in cd else cd, fmt)
                return dt.timestamp() >= time.time() - 7 * 86400
            except (ValueError, TypeError):
                continue
    return True


# --------------------------- Pipeline -------------------------------------- #


def harvest(min_score: float = 0.30, limit: int = 5000) -> dict:
    _hydrate_known_env_files()
    keywords = list(DEFAULT_KEYWORDS)
    sam_env_name, sam_key = _first_nonempty_env(
        "SAM_API_KEY",
        "SAM_GOV_API_KEY",
        "DATA_GOV_API_KEY_PRIMARY",
    )

    print("[harvest] grants.gov ...")
    g = fetch_grants_gov(rows=200, keywords=keywords[:8])
    print(f"  {len(g)} records")

    print("[harvest] sbir.gov ...")
    s = fetch_sbir_gov(keywords[:6])
    print(f"  {len(s)} records")

    sam_status = f"key set via {sam_env_name}" if sam_key else "NO KEY -- skipping"
    print(f"[harvest] sam.gov ({sam_status}) ...")
    sm = fetch_sam_gov(sam_key, days=60, limit=200)
    print(f"  {len(sm)} records")

    raw = (g + s + sm)[:limit]
    print(f"[harvest] total raw: {len(raw)}")

    # First-pass score on titles only, take top 150 for synopsis enrichment
    pre: list[tuple[float, dict]] = []
    for rec in raw:
        if not is_actionable(rec):
            continue
        sc, _ = score_fit(rec, keywords)
        pre.append((sc, rec))
    pre.sort(key=lambda x: x[0], reverse=True)
    enrich_pool = [r for _, r in pre[:150]]

    print(f"[harvest] enriching synopses for top {len(enrich_pool)} ...")
    n_enriched = enrich_grants_gov_synopsis(enrich_pool, top_n=150)
    print(f"  enriched {n_enriched}")

    scored: list[dict] = []
    for rec in raw:
        if not is_actionable(rec):
            continue
        score, matches = score_fit(rec, keywords)
        if score < min_score:
            continue
        rec["_fit_score"] = round(score, 4)
        rec["_keyword_matches"] = matches
        scored.append(rec)

    scored.sort(key=lambda r: r["_fit_score"], reverse=True)

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    raw_path = OUT / f"harvest_{stamp}.json"
    raw_path.write_text(json.dumps({
        "harvested_utc": now.isoformat(),
        "totals": {"grants_gov": len(g), "sbir_gov": len(s), "sam_gov": len(sm)},
        "records": raw,
    }, indent=2, default=str), encoding="utf-8")

    ranked_path = OUT / "ranked.json"
    ranked_payload = {
        "generated_utc": now.isoformat(),
        "min_score": min_score,
        "total_actionable": len(scored),
        "records": scored,
    }
    tmp = ranked_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ranked_payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(ranked_path)

    queue_path = OUT / "queue.jsonl"
    with queue_path.open("w", encoding="utf-8") as fh:
        for rec in scored[:200]:
            fh.write(json.dumps({
                "id": rec.get("id"),
                "source": rec.get("source"),
                "title": rec.get("title"),
                "agency": rec.get("agency"),
                "close_date": rec.get("close_date"),
                "fit_score": rec["_fit_score"],
                "matches": rec["_keyword_matches"],
                "url": rec.get("url"),
                "approval_state": "draft",
            }, default=str) + "\n")

    print(f"[harvest] {len(scored)} actionable >= score {min_score}")
    print(f"[harvest] raw  -> {raw_path}")
    print(f"[harvest] rank -> {ranked_path}")
    print(f"[harvest] queue-> {queue_path}")
    return ranked_payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=float, default=0.30)
    ap.add_argument("--limit", type=int, default=5000)
    args = ap.parse_args()
    harvest(min_score=args.min_score, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
