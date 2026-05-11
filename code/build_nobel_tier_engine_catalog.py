#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Set, Tuple

STACK_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = STACK_ROOT / "out" / "execution" / "universe_map"

SOURCE_MAP_JSON = OUT_DIR / "lumencore_universe_map.json"
SOURCE_ASSETS_CSV = OUT_DIR / "lumencore_universe_assets.csv"

OUTPUT_JSON = OUT_DIR / "lumencore_nobel_engine_catalog.json"
OUTPUT_MD = OUT_DIR / "lumencore_nobel_engine_catalog.md"
OUTPUT_CSV = OUT_DIR / "lumencore_nobel_engine_catalog_summary.csv"
OUTPUT_SHA = OUT_DIR / "lumencore_nobel_engine_catalog_sha256.json"
OUTPUT_HISTORY = OUT_DIR / "lumencore_nobel_engine_catalog_history.jsonl"

ALPHA_PERFORMANCE_JSON = (
    STACK_ROOT / "out" / "unified_alpha" / "_QUARANTINED_2026-05-05" / "unified_alpha_performance.json"
)
ALPHA_SIGNALS_JSON = STACK_ROOT / "out" / "unified_alpha" / "_QUARANTINED_2026-05-05" / "unified_alpha_signals.json"
SPORTS_ALPHA_BOARD_JSON = STACK_ROOT / "out" / "sports_intelligence" / "_dk_alpha_board.json"
EDGE_RANKED_JSON = STACK_ROOT / "out" / "universal_edge" / "_cross_domain_ranked.json"
FULL_BEAST_SUMMARY_JSON = STACK_ROOT / "full_beast_summary.json"
HARMONIC_INFRA_PROOF_JSON = STACK_ROOT / "institutional_harmonic_infrastructure_proof.json"
INSTITUTIONAL_SUMMARY_JSON = STACK_ROOT / "institutional_summary.json"

CATEGORY_ORDER = [
    "dashboard",
    "proof_artifact",
    "script",
    "dataset",
    "document",
    "patent_grant_business_doc",
    "unity_xr_asset",
    "other",
]

REQUIRED_COVERAGE = ["dashboard", "proof_artifact", "script", "dataset"]

MIN_CANONICAL_SCORE = {
    "dashboard": 10,
    "proof_artifact": 10,
    "script": 9,
    "dataset": 8,
    "document": 8,
    "patent_grant_business_doc": 9,
    "unity_xr_asset": 8,
    "other": 10,
}

CANONICAL_LIMIT_PER_CATEGORY = 8

GLOBAL_PROJECT_MARKERS = [
    "/lumatrader/",
    "/institutional_stack_v2/",
    "/lumencore/",
    "/lumengov/",
    "/lumenlab/",
    "/lumasniper/",
    "/lumalive/",
    "/lumatraderv2/",
    "/lumencoretrader/",
    "/lumencoreresearch/",
    "/lumencore_energy_lab/",
    "/lumencore_worldmodel_lab/",
    "/flowform_tournament/",
    "/whitehole/",
    "/whiteholelab/",
    "/iclouddrive/lumatrader/",
    "/iclouddrive/lumencore/",
    "/iclouddrive/lumengov/",
]

PREFERRED_ROOT_MARKERS = [
    "c:/lumatrader/",
    "c:/users/novac/lumatrader/",
    "c:/users/novac/iclouddrive/lumatrader/",
    "c:/users/novac/lumencore/",
    "c:/users/novac/lumengov/",
    "c:/users/novac/lumenlab/",
    "c:/users/novac/lumasniper/",
    "c:/users/novac/lumalive/",
    "c:/users/novac/lumencoretrader/",
    "c:/users/novac/lumencoreresearch/",
    "c:/users/novac/lumencore_energy_lab/",
    "c:/users/novac/lumencore_worldmodel_lab/",
    "c:/whitehole/",
    "c:/whiteholelab/",
]

HARD_EXCLUDE_MARKERS = [
    "/.git/",
    "/.vscode/",
    "/appdata/",
    "/application data/",
    "/node_modules/",
    "/tor browser/",
    "/windows/",
    "/program files/",
    "/library/packagecache/",
    "/library/bee/",
    "/site-packages/",
    "/dist-packages/",
    "/lib/python",
    "/env311/",
    "/.venv/",
    "/.ssh/",
    "/.prefect/",
    "/.streamlit/",
    "/.node-red/",
    "desktop.ini",
    "ntuser.dat",
]

MIRROR_REWRITE_RULES = [
    ("c:/users/novac/iclouddrive/lumatrader/", "c:/lumatrader/"),
    (
        "c:/lumatrader/institutional_stack_v2/.deploy_stage/",
        "c:/lumatrader/institutional_stack_v2/",
    ),
    (
        "c:/lumatrader/institutional_stack_v2/data/code/",
        "c:/lumatrader/institutional_stack_v2/code/",
    ),
]

ENGINE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "engine_id": "trading_institutional_stack",
        "name": "LumaTrader / Institutional Stack",
        "purpose": "Trading intelligence, market data ingestion, strategy testing, live or paper execution, and evidence dashboards.",
        "who_buys": "Funds, prop desks, fintech labs, institutional analytics groups",
        "why_it_matters": "Converts fragmented market telemetry into ranked, auditable execution decisions with proof rails.",
        "keywords": ["lumatrader", "institutional_stack_v2", "execution", "strategy", "trading", "rolling_capital", "mission_control"],
        "path_markers": ["institutional_stack_v2", "rolling_capital", "roi_dashboard", "live_deploy", "proof_engine"],
    },
    {
        "engine_id": "kraken_lumasniper",
        "name": "Kraken Trader / LumaSniper",
        "purpose": "Crypto API integration, symbol readiness, kill switch controls, paper or live toggles, and verified transaction telemetry.",
        "who_buys": "Crypto traders, automated strategy builders, boutique funds",
        "why_it_matters": "Supplies controlled execution with hard guardrails and transaction evidence.",
        "keywords": ["kraken", "lumasniper", "symbol_registry", "kill_switch", "live_executor", "paper"],
        "path_markers": ["kraken", "lumasniper", "symbol_registry", "truth_check", "paper_trade"],
    },
    {
        "engine_id": "lumengov_grant_factory",
        "name": "LumenGov / Grant Factory",
        "purpose": "Federal opportunity discovery and proposal packaging for SBIR or DOE or DARPA-aligned tracks.",
        "who_buys": "Startups, inventors, grant consultants, government contractors",
        "why_it_matters": "Compresses proposal cycles while preserving capability and evidence traceability.",
        "keywords": ["lumengov", "grant", "sbir", "darpa", "doe", "proposal", "capability_statement"],
        "path_markers": ["lumengov", "grants", "sbir", "doe", "darpa", "federal_brief"],
    },
    {
        "engine_id": "infrastructure_outage_prevention",
        "name": "Infrastructure / Outage Prevention Engine",
        "purpose": "Snapshot baselines, detect drift, and trigger evidence-backed divergence alerts before outages.",
        "who_buys": "Data centers, telecom operators, utilities, hospital IT, manufacturing ops",
        "why_it_matters": "Transforms operations from reactive recovery to proactive integrity enforcement.",
        "keywords": ["infrastructure", "snapshot", "drift", "baseline", "frozen_delta", "audit", "uptime"],
        "path_markers": ["infra", "audit_pack", "snapshot", "truth_audit", "frozen_delta", "outage"],
    },
    {
        "engine_id": "lumascout_digital_scout",
        "name": "LumaScout / Digital Scout",
        "purpose": "Crawl public signals to rank emerging artists, creators, or target profiles by momentum and velocity.",
        "who_buys": "Labels, agencies, scouting teams, creator economy investors",
        "why_it_matters": "Creates an early signal advantage in talent and opportunity sourcing.",
        "keywords": ["lumascout", "artist", "creator", "engagement", "momentum", "scout"],
        "path_markers": ["lumascout", "artist", "creator", "scout"],
    },
    {
        "engine_id": "sports_signal_engine",
        "name": "Sports Signal Engine",
        "purpose": "Ingest sports odds and movement, score edge opportunities, and publish auditable betting analytics.",
        "who_buys": "Sports analytics users, media desks, bettors, fantasy operators",
        "why_it_matters": "Turns odds noise into ranked decision rails with explicit confidence context.",
        "keywords": ["sports", "odds", "draftkings", "ev_ranked", "alpha_board", "bookmaker"],
        "path_markers": ["sports", "draftkings", "sportsbook", "alpha_board", "odds"],
    },
    {
        "engine_id": "unified_alpha_engine",
        "name": "Unified Alpha Engine",
        "purpose": "Fuse cross-asset opportunity signals into ranked alpha with confidence, expected value, and Kelly sizing.",
        "who_buys": "Multi-asset desks, research teams, strategy incubators, family offices",
        "why_it_matters": "Turns fragmented market edges into one auditable alpha feed that can be promoted into execution.",
        "keywords": ["unified_alpha", "alpha_engine", "cross_asset", "kelly", "expected_value", "moonshot"],
        "path_markers": ["unified_alpha", "alpha_signals", "alpha_performance", "unified_trade"],
    },
    {
        "engine_id": "edgefinding_universal_engine",
        "name": "Universal Edgefinding Engine",
        "purpose": "Rank cross-domain signals with harmonic and flowform weighting to surface highest-impact edge candidates.",
        "who_buys": "Signal intelligence teams, portfolio allocators, risk labs, autonomous decision systems",
        "why_it_matters": "Provides explainable edge ranking across sports and crypto with consistent scoring semantics.",
        "keywords": ["universal_edge", "edgefinding", "cross_domain", "flowform", "harmonic", "sharpity"],
        "path_markers": ["universal_edge", "cross_domain_ranked", "flowform_ranked", "sports_ranked", "crypto_ranked"],
    },
    {
        "engine_id": "quant_lab_harmonic_engine",
        "name": "Quant Lab Harmonic Engine",
        "purpose": "Run large candidate sweeps and harmonic validation to select institutional-grade strategy champions.",
        "who_buys": "Quant labs, institutional allocators, research engineering teams",
        "why_it_matters": "Demonstrates measurable champion quality with reproducible Sharpe-level proof and lineage artifacts.",
        "keywords": ["quant_lab", "harmonic", "full_beast", "institutional_harmonic", "test_sharpe", "leaderboard"],
        "path_markers": ["full_beast", "institutional_harmonic", "institutional_summary", "leaderboard", "validation"],
    },
    {
        "engine_id": "crowdfunding_engine",
        "name": "CrowdFunding Engine",
        "purpose": "Scan campaign ecosystems for traction, founder credibility, and early asymmetric opportunity.",
        "who_buys": "Angel networks, product scouts, trend research groups",
        "why_it_matters": "Identifies high-upside campaigns before broad-market visibility peaks.",
        "keywords": ["crowdfund", "kickstarter", "indiegogo", "campaign", "founder", "backer"],
        "path_markers": ["crowdfund", "kickstarter", "indiegogo", "campaign", "backer"],
    },
    {
        "engine_id": "cyber_forensics_engine",
        "name": "Cyber / Digital Forensics Engine",
        "purpose": "Assist investigations with anomaly triage, evidence linking, and report-ready chronology.",
        "who_buys": "Security firms, legal teams, incident response providers",
        "why_it_matters": "Reduces analysis latency while improving evidentiary clarity.",
        "keywords": ["forensic", "incident", "triage", "cyber", "investigation", "evidence"],
        "path_markers": ["forensic", "incident", "cyber", "chain_of_custody", "evidence"],
    },
    {
        "engine_id": "identity_echoform_twin",
        "name": "Identity / EchoForm / Digital Twin Engine",
        "purpose": "Build identity graphs, memory architectures, and digital twin representations.",
        "who_buys": "Personal AI platforms, simulation companies, AR or VR identity products",
        "why_it_matters": "Establishes continuity layers for person-centric intelligence systems.",
        "keywords": ["echoform", "digital_twin", "identity", "memory_model", "essencecore", "cognitivecontinuity"],
        "path_markers": ["echoform", "digital_twin", "identity", "essencecore", "cognitivecontinuity"],
    },
    {
        "engine_id": "unity_xr_luma_live_command",
        "name": "Unity XR / Luma Live Command",
        "purpose": "Immersive command HUDs and demo environments for live system-state visualization.",
        "who_buys": "Defense training, simulation labs, investor demo teams, museums",
        "why_it_matters": "Converts complex system intelligence into embodied real-time interfaces.",
        "keywords": ["unity", "xr", "holo", "command_room", "luma_live_command", "lumaexperience"],
        "path_markers": ["unity", "xr", "holo", "lumaexperience", "live_command"],
    },
    {
        "engine_id": "smart_city_telecom_engine",
        "name": "Smart City / Telecom Engine",
        "purpose": "Edge signal routing for IoT meshes, smart infrastructure, and telecom telemetry.",
        "who_buys": "Cities, utilities, telecom integrators, infrastructure operators",
        "why_it_matters": "Provides low-latency situational intelligence at the edge.",
        "keywords": ["smart_city", "iot", "telecom", "sensor", "edge_compute", "utility"],
        "path_markers": ["smart_city", "iot", "telecom", "sensor", "utility"],
    },
    {
        "engine_id": "flowform_hardware_geometry",
        "name": "FlowForm / Hardware Geometry Engine",
        "purpose": "Hardware geometry and routing concepts for thermal or electromagnetic optimization.",
        "who_buys": "OEM hardware teams, EV and robotics labs, aerospace design groups",
        "why_it_matters": "Creates licensable architecture primitives that can improve hardware efficiency.",
        "keywords": ["flowform", "hardware", "motherboard", "honeycomb", "thermal", "cymatic", "spiral"],
        "path_markers": ["flowform", "hardware", "honeycomb", "thermal", "cymatic"],
    },
    {
        "engine_id": "energy_nuclear_harmonization",
        "name": "Energy / Nuclear Harmonization Engine",
        "purpose": "High-field simulation and harmonization research for energy environments.",
        "who_buys": "DOE-aligned labs, advanced energy companies, defense R&D teams",
        "why_it_matters": "Adds structured simulation intelligence to difficult high-EMI contexts.",
        "keywords": ["energy", "nuclear", "field_stabilization", "radiation", "high_emi", "harmonization"],
        "path_markers": ["energy", "nuclear", "field_stabilization", "harmonization", "radiation"],
    },
    {
        "engine_id": "world_model_cross_sector",
        "name": "World Model / Cross-Sector Engine",
        "purpose": "Unify data across sectors to simulate drift, failure, and opportunity outcomes.",
        "who_buys": "Enterprise strategy offices, government analytics teams, operational command groups",
        "why_it_matters": "Delivers cross-domain decision support using one coherent model fabric.",
        "keywords": ["worldmodel", "cross_sector", "scenario", "multisector", "opportunity_intel", "failure_predictions"],
        "path_markers": ["worldmodel", "cross_sector", "scenario", "opportunity", "multisector"],
    },
    {
        "engine_id": "lumacore_orchestrator",
        "name": "LumaCore Agent / Orchestrator",
        "purpose": "Master routing and memory agent that activates subsystems, promotes champions, and assembles proof packs.",
        "who_buys": "Internal operations first, then enterprise automation teams",
        "why_it_matters": "Transforms the portfolio from isolated tools into an operating system.",
        "keywords": ["orchestrator", "router", "controller", "watchdog", "master_agent", "mission_control"],
        "path_markers": ["orchestrator", "mission_control", "controller", "router", "watchdog"],
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_path(path: Path) -> str:
    return path.as_posix()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class AssetRow:
    path: str
    path_lower: str
    root: str
    categories: Set[str]
    engines: Set[str]
    extension: str
    size_bytes: int


def parse_assets_csv(path: Path) -> List[AssetRow]:
    rows: List[AssetRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            p = (row.get("path") or "").strip()
            if not p:
                continue
            cats = set(filter(None, (row.get("categories") or "").split(";")))
            engs = set(filter(None, (row.get("engines") or "").split(";")))
            ext = (row.get("extension") or "").strip().lower()
            root = (row.get("root") or "").strip()
            try:
                size = int(float(row.get("size_bytes") or 0))
            except Exception:
                size = 0
            rows.append(
                AssetRow(
                    path=p,
                    path_lower=p.lower(),
                    root=root,
                    categories=cats,
                    engines=engs,
                    extension=ext,
                    size_bytes=size,
                )
            )
    return rows


def contains_any(path_lower: str, markers: Iterable[str]) -> bool:
    return any(marker in path_lower for marker in markers)


def keyword_hits(path_lower: str, keywords: Iterable[str]) -> int:
    return sum(1 for kw in keywords if kw and kw in path_lower)


def preferred_path_bonus(path_lower: str) -> int:
    return 4 if contains_any(path_lower, PREFERRED_ROOT_MARKERS) else 0


def category_bias(categories: Set[str]) -> int:
    score = 0
    if "proof_artifact" in categories:
        score += 3
    if "dashboard" in categories:
        score += 2
    if "script" in categories:
        score += 2
    if "dataset" in categories:
        score += 1
    if "document" in categories:
        score += 1
    if "patent_grant_business_doc" in categories:
        score += 1
    if "unity_xr_asset" in categories:
        score += 1
    return score


def canonical_key(path_lower: str) -> str:
    out = path_lower
    for before, after in MIRROR_REWRITE_RULES:
        out = out.replace(before, after)
    while "//" in out:
        out = out.replace("//", "/")
    return out


def is_project_scoped(path_lower: str) -> bool:
    return contains_any(path_lower, GLOBAL_PROJECT_MARKERS)


def is_excluded(path_lower: str) -> bool:
    return contains_any(path_lower, HARD_EXCLUDE_MARKERS)


def eligible_for_engine(row: AssetRow, engine: Dict[str, Any]) -> bool:
    if is_excluded(row.path_lower):
        return False
    if not is_project_scoped(row.path_lower):
        return False

    eid = engine["engine_id"]
    engine_keywords = [k.lower() for k in engine["keywords"]]
    path_markers = [k.lower() for k in engine["path_markers"]]

    kh = keyword_hits(row.path_lower, engine_keywords)
    ph = keyword_hits(row.path_lower, path_markers)
    tagged = eid in row.engines

    if tagged and (kh + ph) >= 1:
        return True
    if ph >= 2:
        return True
    if ph >= 1 and kh >= 1:
        return True
    return False


def score_asset_for_engine(row: AssetRow, engine: Dict[str, Any]) -> int:
    score = 0
    eid = engine["engine_id"]
    if eid in row.engines:
        score += 8

    kh = keyword_hits(row.path_lower, (k.lower() for k in engine["keywords"]))
    ph = keyword_hits(row.path_lower, (k.lower() for k in engine["path_markers"]))
    score += min(12, kh * 2 + ph * 3)
    score += preferred_path_bonus(row.path_lower)
    score += category_bias(row.categories)

    if "/out/execution/" in row.path_lower or "/reports/" in row.path_lower:
        score += 1
    return score


def build_performance_snapshot(engine_id: str) -> Dict[str, Any]:
    if engine_id == "sports_signal_engine":
        board = read_json_if_exists(SPORTS_ALPHA_BOARD_JSON)
        quantstats = board.get("quantstats") or {}
        top_pick = board.get("top_pick") or {}
        rows = board.get("rows") if isinstance(board.get("rows"), list) else []
        top_row = rows[0] if rows else {}
        return {
            "source": normalize_path(SPORTS_ALPHA_BOARD_JSON),
            "generated_utc": board.get("generated_utc"),
            "quantstats_sharpe": coerce_float(quantstats.get("sharpe")),
            "top_pick_edge_pct": coerce_float(top_pick.get("edge_pct")),
            "top_pick_alpha_score_v2": coerce_float(top_pick.get("alpha_score_v2")),
            "top_pick_fair_price_pin": coerce_float(top_row.get("fair_price_pin")),
            "top_pick_market_price": coerce_float(top_row.get("dk_price_decimal")),
        }

    if engine_id == "unified_alpha_engine":
        perf = read_json_if_exists(ALPHA_PERFORMANCE_JSON)
        sig = read_json_if_exists(ALPHA_SIGNALS_JSON)
        signal_rows = sig.get("signals") if isinstance(sig.get("signals"), list) else []
        top_signal = signal_rows[0] if signal_rows else {}
        return {
            "source": normalize_path(ALPHA_PERFORMANCE_JSON),
            "generated_utc": perf.get("generated_utc"),
            "total_signals": coerce_int(perf.get("total_signals")),
            "avg_expected_value_pct": coerce_float(perf.get("avg_expected_value_pct")),
            "avg_confidence_pct": coerce_float(perf.get("avg_confidence_pct")),
            "avg_historical_win_rate": coerce_float(perf.get("avg_historical_win_rate")),
            "top_signal_expected_value_pct": coerce_float(top_signal.get("expected_value_pct")),
            "top_signal_kelly_f": coerce_float(top_signal.get("kelly_f")),
        }

    if engine_id == "edgefinding_universal_engine":
        ranked = read_json_if_exists(EDGE_RANKED_JSON)
        summary = ranked.get("summary") or {}
        sports = summary.get("sports") or {}
        crypto = summary.get("crypto") or {}
        top_rows = ranked.get("top_signals") if isinstance(ranked.get("top_signals"), list) else []
        top_signal = top_rows[0] if top_rows else {}
        flowform = top_signal.get("flowform") or {}
        return {
            "source": normalize_path(EDGE_RANKED_JSON),
            "generated_utc": ranked.get("generated_utc"),
            "total_ranked_signals": coerce_int(ranked.get("total")),
            "sports_top_harmonic_score": coerce_float(sports.get("top_score")),
            "crypto_top_harmonic_score": coerce_float(crypto.get("top_score")),
            "top_signal_edge_pct": coerce_float(top_signal.get("edge_pct")),
            "top_signal_hybrid_harmonic_score": coerce_float(flowform.get("hybrid_harmonic_score")),
            "top_signal_sharpity_score": coerce_float(flowform.get("sharpity_score")),
        }

    if engine_id == "quant_lab_harmonic_engine":
        harmonic = read_json_if_exists(HARMONIC_INFRA_PROOF_JSON)
        harmonic_summary = harmonic.get("summary") or {}
        full_beast = read_json_if_exists(FULL_BEAST_SUMMARY_JSON)
        inst_summary = read_json_if_exists(INSTITUTIONAL_SUMMARY_JSON)
        return {
            "sources": [
                normalize_path(HARMONIC_INFRA_PROOF_JSON),
                normalize_path(FULL_BEAST_SUMMARY_JSON),
                normalize_path(INSTITUTIONAL_SUMMARY_JSON),
            ],
            "harmonic_generated_utc": harmonic.get("timestamp_utc"),
            "harmonic_top_test_sharpe": coerce_float(harmonic_summary.get("top_test_sharpe")),
            "full_beast_top_test_sharpe": coerce_float(full_beast.get("top_test_sharpe")),
            "institutional_top_test_sharpe": coerce_float(inst_summary.get("top_test_sharpe")),
            "full_beast_candidates_scored": coerce_int(full_beast.get("actual_candidates_scored")),
            "harmonic_rows_scored": coerce_int(harmonic_summary.get("rows")),
        }

    return {}


def licensing_model_for_engine(engine_id: str) -> Dict[str, Any]:
    if engine_id in {
        "trading_institutional_stack",
        "kraken_lumasniper",
        "sports_signal_engine",
        "unified_alpha_engine",
        "edgefinding_universal_engine",
        "quant_lab_harmonic_engine",
    }:
        return {
            "sku": "Signal Intelligence Suite",
            "tiers": ["Pilot monthly seat", "Team annual", "Enterprise private deployment"],
            "commercial_style": "Seat plus execution-volume add-on",
        }
    if engine_id in {"lumengov_grant_factory", "cyber_forensics_engine", "infrastructure_outage_prevention"}:
        return {
            "sku": "Evidence Automation Suite",
            "tiers": ["Consulting assisted", "Agency annual", "Government hardened deployment"],
            "commercial_style": "Annual license plus support retainer",
        }
    if engine_id in {"unity_xr_luma_live_command", "identity_echoform_twin", "flowform_hardware_geometry", "energy_nuclear_harmonization"}:
        return {
            "sku": "R&D and IP Suite",
            "tiers": ["Demo license", "Lab license", "OEM or institutional licensing"],
            "commercial_style": "License plus integration and IP terms",
        }
    return {
        "sku": "Modular Engine License",
        "tiers": ["Pilot", "Production", "Enterprise"],
        "commercial_style": "Annual license",
    }


def readiness_score(canonical_assets: Dict[str, List[Dict[str, Any]]], missing_required: List[str]) -> float:
    q = {c: len(canonical_assets.get(c, [])) for c in CATEGORY_ORDER}

    base = 0.0
    base += 18.0 if q["dashboard"] >= 2 else 10.0 if q["dashboard"] >= 1 else 0.0
    base += 18.0 if q["proof_artifact"] >= 2 else 10.0 if q["proof_artifact"] >= 1 else 0.0
    base += 18.0 if q["script"] >= 2 else 10.0 if q["script"] >= 1 else 0.0
    base += 14.0 if q["dataset"] >= 2 else 8.0 if q["dataset"] >= 1 else 0.0
    base += 10.0 if q["document"] >= 2 else 5.0 if q["document"] >= 1 else 0.0
    base += 8.0 if q["patent_grant_business_doc"] >= 2 else 4.0 if q["patent_grant_business_doc"] >= 1 else 0.0
    base += 4.0 if q["unity_xr_asset"] >= 1 else 0.0

    all_scores = [r["score"] for cat_assets in canonical_assets.values() for r in cat_assets]
    if all_scores:
        specificity = max(0.35, min(1.0, mean(all_scores) / 24.0))
    else:
        specificity = 0.35

    penalty = 12.0 * len(missing_required)
    final = max(0.0, min(100.0, base * specificity - penalty))
    return round(final, 2)


def build_engine_catalog(rows: List[AssetRow]) -> List[Dict[str, Any]]:
    catalog: List[Dict[str, Any]] = []

    for engine in ENGINE_DEFINITIONS:
        engine_id = engine["engine_id"]

        scored: List[Tuple[int, AssetRow]] = []
        for row in rows:
            if not eligible_for_engine(row, engine):
                continue
            score = score_asset_for_engine(row, engine)
            if score <= 0:
                continue
            scored.append((score, row))

        scored.sort(key=lambda x: (x[0], x[1].size_bytes), reverse=True)

        by_category: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CATEGORY_ORDER}
        category_counts: Dict[str, int] = {c: 0 for c in CATEGORY_ORDER}
        seen_keys: Dict[str, Set[str]] = {c: set() for c in CATEGORY_ORDER}

        for score, row in scored:
            row_categories = [c for c in CATEGORY_ORDER if c in row.categories]
            if not row_categories:
                row_categories = ["other"]

            for c in row_categories:
                category_counts[c] += 1

                if score < MIN_CANONICAL_SCORE.get(c, 10):
                    continue
                if len(by_category[c]) >= CANONICAL_LIMIT_PER_CATEGORY:
                    continue

                key = canonical_key(row.path_lower)
                if key in seen_keys[c]:
                    continue
                seen_keys[c].add(key)

                by_category[c].append(
                    {
                        "path": row.path,
                        "score": score,
                        "size_bytes": row.size_bytes,
                        "extension": row.extension,
                    }
                )

        missing = [c for c in REQUIRED_COVERAGE if len(by_category.get(c, [])) == 0]
        licensing = licensing_model_for_engine(engine_id)
        readiness = readiness_score(by_category, missing)
        performance_snapshot = build_performance_snapshot(engine_id)

        all_selected_scores = [r["score"] for cat_assets in by_category.values() for r in cat_assets]

        catalog.append(
            {
                "engine_id": engine_id,
                "name": engine["name"],
                "one_pager": {
                    "what_it_does": engine["purpose"],
                    "who_buys_it": engine["who_buys"],
                    "why_it_matters": engine["why_it_matters"],
                    "licensing_model": licensing,
                },
                "artifact_counts": category_counts,
                "canonical_asset_counts": {c: len(by_category.get(c, [])) for c in CATEGORY_ORDER},
                "selection_stats": {
                    "eligible_rows": len(scored),
                    "selected_assets": len(all_selected_scores),
                    "avg_selected_score": round(mean(all_selected_scores), 2) if all_selected_scores else 0.0,
                },
                "performance_snapshot": performance_snapshot,
                "readiness_score_0_100": readiness,
                "missing_required_artifacts": missing,
                "canonical_assets": by_category,
            }
        )

    catalog.sort(key=lambda x: x["readiness_score_0_100"], reverse=True)
    return catalog


def render_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# LumenCore Nobel Tier Engine Catalog")
    lines.append("")
    lines.append(f"Generated UTC: {payload['generated_utc']}")
    lines.append(f"Source map: {payload['source_universe_map']}")
    lines.append(f"Source assets: {payload['source_assets_csv']}")
    lines.append("")

    lines.append("## Portfolio Summary")
    lines.append(f"- Engines cataloged: {len(payload['engines'])}")
    lines.append(f"- Assets source rows: {payload['assets_source_rows']}")
    lines.append("")

    lines.append("## Engine Cards")
    for engine in payload["engines"]:
        one = engine["one_pager"]
        lines.append(f"### {engine['name']}")
        lines.append(f"- Engine ID: {engine['engine_id']}")
        lines.append(f"- What it does: {one['what_it_does']}")
        lines.append(f"- Who buys it: {one['who_buys_it']}")
        lines.append(f"- Why it matters: {one['why_it_matters']}")
        lines.append(f"- Readiness score: {engine['readiness_score_0_100']}")

        snapshot = engine.get("performance_snapshot") or {}
        if snapshot:
            lines.append("- Performance snapshot:")
            for key, value in snapshot.items():
                if value is None or isinstance(value, (dict, list)):
                    continue
                lines.append(f"  - {key}: {value}")
            if isinstance(snapshot.get("sources"), list):
                lines.append("  - sources: " + ", ".join(snapshot["sources"]))
            elif snapshot.get("source"):
                lines.append(f"  - source: {snapshot['source']}")

        if engine["missing_required_artifacts"]:
            lines.append("- Missing required artifact classes: " + ", ".join(engine["missing_required_artifacts"]))
        else:
            lines.append("- Missing required artifact classes: none")

        stats = engine["selection_stats"]
        lines.append(
            "- Selection stats: "
            f"eligible_rows={stats['eligible_rows']}, "
            f"selected_assets={stats['selected_assets']}, "
            f"avg_selected_score={stats['avg_selected_score']}"
        )

        licensing = one["licensing_model"]
        lines.append(f"- SKU: {licensing['sku']}")
        lines.append(f"- Commercial style: {licensing['commercial_style']}")
        lines.append(f"- Tiers: {', '.join(licensing['tiers'])}")

        lines.append("- Canonical assets by category:")
        for c in CATEGORY_ORDER:
            assets = engine["canonical_assets"].get(c, [])
            if not assets:
                continue
            lines.append(f"  - {c} ({len(assets)} selected / {engine['artifact_counts'].get(c, 0)} eligible)")
            for row in assets[:4]:
                lines.append(f"    - {row['path']}")
        lines.append("")

    lines.append("## Chain of Custody")
    lines.append("- Source assets were read-only.")
    lines.append("- Catalog artifacts were generated as new files.")
    lines.append("- SHA256 manifest generated for catalog outputs.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_summary_csv(path: Path, engines: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "engine_id",
                "name",
                "readiness_score_0_100",
                "eligible_rows",
                "selected_assets",
                "avg_selected_score",
                "dashboard_selected",
                "proof_selected",
                "script_selected",
                "dataset_selected",
                "document_selected",
                "business_doc_selected",
                "missing_required_artifacts",
                "proof_primary_metric",
                "proof_primary_value",
                "proof_secondary_metric",
                "proof_secondary_value",
                "sku",
                "commercial_style",
            ]
        )
        for engine in engines:
            stats = engine["selection_stats"]
            counts = engine["canonical_asset_counts"]
            licensing = engine["one_pager"]["licensing_model"]
            snapshot = engine.get("performance_snapshot") or {}

            metric_preference = [
                "harmonic_top_test_sharpe",
                "full_beast_top_test_sharpe",
                "institutional_top_test_sharpe",
                "quantstats_sharpe",
                "top_pick_edge_pct",
                "top_signal_sharpity_score",
                "top_signal_hybrid_harmonic_score",
                "top_signal_edge_pct",
                "avg_expected_value_pct",
                "avg_confidence_pct",
            ]
            picked = [(k, snapshot.get(k)) for k in metric_preference if snapshot.get(k) is not None]
            primary_metric, primary_value = (picked[0] if picked else ("", ""))
            secondary_metric, secondary_value = (picked[1] if len(picked) > 1 else ("", ""))

            writer.writerow(
                [
                    engine["engine_id"],
                    engine["name"],
                    engine["readiness_score_0_100"],
                    stats["eligible_rows"],
                    stats["selected_assets"],
                    stats["avg_selected_score"],
                    counts.get("dashboard", 0),
                    counts.get("proof_artifact", 0),
                    counts.get("script", 0),
                    counts.get("dataset", 0),
                    counts.get("document", 0),
                    counts.get("patent_grant_business_doc", 0),
                    ";".join(engine.get("missing_required_artifacts", [])),
                    primary_metric,
                    primary_value,
                    secondary_metric,
                    secondary_value,
                    licensing.get("sku"),
                    licensing.get("commercial_style"),
                ]
            )


def append_history(path: Path, payload: Dict[str, Any]) -> None:
    row = {
        "generated_utc": payload["generated_utc"],
        "engine_count": len(payload["engines"]),
        "assets_source_rows": payload["assets_source_rows"],
        "top_readiness": [
            {
                "engine_id": e["engine_id"],
                "readiness_score_0_100": e["readiness_score_0_100"],
                "missing_required_artifacts": e["missing_required_artifacts"],
            }
            for e in payload["engines"][:10]
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    if not SOURCE_MAP_JSON.exists() or not SOURCE_ASSETS_CSV.exists():
        raise SystemExit("Required source artifacts missing. Run build_lumencore_universe_map.py first.")

    _map_payload = read_json(SOURCE_MAP_JSON)
    rows = parse_assets_csv(SOURCE_ASSETS_CSV)
    engines = build_engine_catalog(rows)

    payload = {
        "generated_utc": now_utc(),
        "schema": "lumencore_nobel_tier_engine_catalog_v3",
        "source_universe_map": normalize_path(SOURCE_MAP_JSON),
        "source_assets_csv": normalize_path(SOURCE_ASSETS_CSV),
        "assets_source_rows": len(rows),
        "engines": engines,
        "safeguards": {
            "raw_data_mutated": False,
            "raw_data_deleted": False,
            "snapshot_only_output": True,
            "hard_exclude_filters": True,
            "engine_specific_path_filters": True,
            "mirror_dedupe": True,
        },
        "artifacts": {
            "json": normalize_path(OUTPUT_JSON),
            "markdown": normalize_path(OUTPUT_MD),
            "summary_csv": normalize_path(OUTPUT_CSV),
            "sha256": normalize_path(OUTPUT_SHA),
            "history": normalize_path(OUTPUT_HISTORY),
        },
    }

    write_json(OUTPUT_JSON, payload)
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    write_summary_csv(OUTPUT_CSV, engines)

    sha_payload = {
        "generated_utc": payload["generated_utc"],
        "files": {
            normalize_path(OUTPUT_JSON): sha256_of_file(OUTPUT_JSON),
            normalize_path(OUTPUT_MD): sha256_of_file(OUTPUT_MD),
            normalize_path(OUTPUT_CSV): sha256_of_file(OUTPUT_CSV),
        },
    }
    write_json(OUTPUT_SHA, sha_payload)

    append_history(OUTPUT_HISTORY, payload)

    print(normalize_path(OUTPUT_JSON))
    print(normalize_path(OUTPUT_MD))
    print(normalize_path(OUTPUT_CSV))
    print(normalize_path(OUTPUT_SHA))
    print(normalize_path(OUTPUT_HISTORY))


if __name__ == "__main__":
    main()
