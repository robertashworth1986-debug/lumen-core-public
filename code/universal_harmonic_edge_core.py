#!/usr/bin/env python3
"""
Universal Harmonic Edge Core
=============================
Single shared engine that scores signals from ANY domain using the same
non-linear harmonic geometry principles that run throughout this stack:

  CRYPTO:       harmonic_signal_connector → live Kraken price series
                → strat_curvature_reversal, strat_resonance_revert, etc.

  SPORTS ODDS:  sports_intelligence_layer → multi-book price manifold
                → curvature (log-odds distance), resonance (vs Pinnacle)

  CROSS-SECTOR: cross_sector_intel_pipeline → infrastructure delta series
                → phase-locking, frequency drift, entropy filtering

These are not different systems. They are all asking the same question:

  "Where is the market/system NOT moving in a straight line?"

Nature does not move in straight lines. Prices, energy grids, crowd
behaviour, liquidity flow — all follow curved, resonant, phase-locked
paths. The edge always lives at the curvature points where linear
models break down. That is what the Fibonacci (phi=1.618) / log
geometry in algo_phase_lattice is probing, what strat_curvature_reversal
detects in price, and what the sports odds curvature score measures in
the multi-book price manifold.

This module gives every project in the stack ONE shared scoring API:

    from universal_harmonic_edge_core import score_signal, CrossDomainAggregator

────────────────────────────────────────────────────────────────────────────────
Universal Signal Schema (works for any domain):
{
    "signal_id":      str   — unique identifier
    "domain":         str   — "crypto" | "sports" | "infra" | "digital_scout"
    "asset":          str   — symbol / event / sector / target
    "signal_type":    str   — "momentum" | "arb" | "value" | "breakout" | "alert"
    "edge_pct":       float — raw edge percentage
    "best_price":     float — best observed price / score in the signal context
    "ref_price":      float — reference/anchor price (Pinnacle, VWAP, benchmark, etc.)
    "worst_price":    float — worst observed (spread width proxy)
    "n_sources":      int   — number of independent data sources (books, exchanges, feeds)
    "is_soft_source": bool  — True if edge comes from a slow/lagging source
    "repeat_count":   int   — how many times this motif has been seen historically
    "scanned_utc":    str   — ISO timestamp
}
────────────────────────────────────────────────────────────────────────────────
"""

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR  = ROOT_DIR / "out" / "universal_edge"

PHI = 1.6180339887   # Golden ratio — base of natural growth geometry


# ── Utilities ─────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _safe(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return d


def _atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


# ── Core Scoring Dimensions ───────────────────────────────────────────────────

def curvature_score(best_price: float, worst_price: float) -> float:
    """
    Log-space dispersion between best and worst observed price.
    Uses natural logarithm — same geometric principle as strat_curvature_reversal
    in harmonic_hybrid_core.py (first + second derivative of price series).

    In price-series terms: second derivative going positive after negative = buy.
    In multi-source terms: log distance between best/worst = manifold curvature.
    Wider log-distance = more curvature = more edge opportunity.

    Normalized to [0, 100] via PHI-scaled divisor (1/PHI ≈ 0.618 = natural saturation).
    """
    if best_price <= 1.0 or worst_price <= 1.0:
        return 0.0
    d = abs(math.log(best_price) - math.log(worst_price))
    return round(_clamp(d / (1.0 / PHI) * 100.0), 4)


def resonance_score(best_price: float, ref_price: float) -> float:
    """
    Sharp-anchor resonance: how far above the reference/anchor is best_price?
    In crypto: reference = VWAP / benchmark strategy score / Sharpe anchor.
    In sports: reference = Pinnacle's implied fair odds.
    In infra:  reference = grid baseline / sector mean loss.

    Mirrors strat_resonance_revert (harmonic_hybrid_core): a Z-score threshold
    where deviation from mean = a tradeable resonance event.

    Positive resonance = price exceeds what the best information source
    considers fair = real edge window.
    """
    if ref_price <= 0.0 or best_price <= 0.0:
        return 0.0
    # excess = (best/ref - 1) as a ratio; scale by 8x for [0,100] normalization
    excess = (best_price / ref_price - 1.0) * 100.0
    return round(_clamp(excess * 8.0), 4)


def persistence_score(repeat_count: int) -> float:
    """
    Saturating exponential persistence proxy.
    Recurring edge motifs indicate structural market inefficiency, not noise.
    Uses e^(-k/6) envelope — matches the decay constant from CLV feedback.

    In novel_harmonic_layers: algo_echo_stack builds multi-scale memory
    (5, 13, 34 windows). This function does the same for cross-scan history.
    """
    return round(_clamp(100.0 * (1.0 - math.exp(-repeat_count / 6.0))), 4)


def sharpity_score(is_soft_source: bool, n_sources: int) -> float:
    """
    Exploitability proxy:
    - Soft source (slow book, lagging feed) = high score = edge is exploitable.
    - Hard/sharp source (Pinnacle, exchange VWAP) = lower score = market efficient.
    - More confirming sources = slightly higher score.

    Mirrors the "smart money vs dumb money" bookmaker profiling in
    sports_intelligence_layer and the 'softness_score' logic.
    """
    base = 80.0 if is_soft_source else 30.0
    source_bonus = min(15.0, n_sources * 1.5)
    return round(_clamp(base + source_bonus), 4)


def phi_resonance_bonus(edge_pct: float) -> float:
    """
    Non-linear bonus for edges that land near Fibonacci / PHI harmonic levels.
    Natural growth compresses around phi ratios (1.618, 2.618, 4.236).
    A 1.6%, 2.6%, or 4.2% raw edge landing near these ratios suggests structural
    rather than noise-driven dislocation — a micro-signature of flow geometry.

    Returns 0–10 bonus added to composite score.
    """
    phi_levels = [PHI, PHI * PHI, PHI ** 3, 1.0 / PHI, 1.0 / (PHI * PHI)]
    closest = min(abs(edge_pct - lvl * 10.0) for lvl in phi_levels)
    # Within 0.5% of a phi level = 10 point bonus, decaying linearly
    return round(max(0.0, 10.0 * (1.0 - closest / 0.5)), 4)


# ── Composite Score ───────────────────────────────────────────────────────────

# Domain-specific default weight profiles
_DOMAIN_WEIGHTS = {
    "crypto": {
        "curvature":   0.30,
        "resonance":   0.40,  # crypto has VWAP/benchmark anchors — resonance matters more
        "persistence": 0.20,
        "sharpity":    0.10,
    },
    "sports": {
        "curvature":   0.35,
        "resonance":   0.35,  # Pinnacle is sharp — resonance and curvature balanced
        "persistence": 0.20,
        "sharpity":    0.10,
    },
    "infra": {
        "curvature":   0.40,  # infrastructure dislocations are geometry-driven
        "resonance":   0.25,
        "persistence": 0.30,  # sector patterns repeat on long cycles
        "sharpity":    0.05,
    },
    "digital_scout": {
        "curvature":   0.30,
        "resonance":   0.30,
        "persistence": 0.35,  # scouting is about pattern recurrence
        "sharpity":    0.05,
    },
}
_DEFAULT_WEIGHTS = {"curvature": 0.35, "resonance": 0.35, "persistence": 0.20, "sharpity": 0.10}


def score_signal(
    edge_pct: float,
    best_price: float,
    ref_price: float,
    worst_price: float,
    n_sources: int,
    is_soft_source: bool,
    repeat_count: int,
    domain: str = "crypto",
    adaptive_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Universal harmonic edge score for any domain signal.
    Returns a dict with all dimension scores + composite.
    """
    w = adaptive_weights or _DOMAIN_WEIGHTS.get(domain, _DEFAULT_WEIGHTS)

    cur  = curvature_score(best_price, worst_price)
    res  = resonance_score(best_price, ref_price)
    per  = persistence_score(repeat_count)
    sha  = sharpity_score(is_soft_source, n_sources)
    phi  = phi_resonance_bonus(edge_pct)

    composite = (
        w["curvature"] * cur
        + w["resonance"] * res
        + w["persistence"] * per
        + w["sharpity"] * sha
        + phi  # phi bonus is additive, not weighted
    )

    return {
        "curvature_score":       cur,
        "resonance_score":       res,
        "persistence_score":     per,
        "sharpity_score":        sha,
        "phi_resonance_bonus":   phi,
        "hybrid_harmonic_score": round(_clamp(composite), 4),
        "weights":               {k: round(v, 6) for k, v in w.items()},
        "domain":                domain,
    }


# ── Cross-Domain Aggregator ───────────────────────────────────────────────────

class CrossDomainAggregator:
    """
    Collects signals from any domain and produces a unified ranked view.
    All signals are scored using score_signal() so they are directly comparable.

    Usage from any module:
        agg = CrossDomainAggregator.load_or_create()
        agg.ingest_signals("sports",  sports_list)
        agg.ingest_signals("crypto",  crypto_list)
        agg.ingest_signals("infra",   infra_list)
        agg.write()
    """

    def __init__(self) -> None:
        self._signals: List[Dict] = []

    @classmethod
    def load_or_create(cls) -> "CrossDomainAggregator":
        return cls()

    def ingest_signals(self, domain: str, signals: List[Dict]) -> None:
        """
        Accept raw signals from any domain and normalize them to the
        universal schema. Domain-specific field mapping is handled here.
        """
        for raw in signals:
            # --- Sports schema ---
            if domain == "sports":
                sig = {
                    "signal_id":     f"sports|{raw.get('event_id','')}|{raw.get('market','')}|{raw.get('outcome','')}",
                    "domain":        "sports",
                    "asset":         f"{raw.get('home_team','')} vs {raw.get('away_team','')} [{raw.get('sport_title','')}]",
                    "signal_type":   raw.get("signal_type", "unknown"),
                    "edge_pct":      _safe(raw.get("edge_pct"), 0.0),
                    "best_price":    _safe(raw.get("best_odds"), 0.0),
                    "ref_price":     _safe(raw.get("pinnacle_price") or raw.get("consensus_odds"), 0.0),
                    "worst_price":   _safe(raw.get("worst_odds"), 0.0),
                    "n_sources":     int(_safe(raw.get("n_books"), 1)),
                    "is_soft_source": raw.get("best_book", "") not in (
                        "pinnacle", "betfair_ex_uk", "betfair_ex_eu", "smarkets", "matchbook"
                    ),
                    "repeat_count":  int(_safe(raw.get("flowform", {}).get("persistence_score", 0) / 10 if isinstance(raw.get("flowform"), dict) else 0)),
                    "scanned_utc":   raw.get("scanned_utc", _now_utc()),
                    "_raw":          raw,
                }

            # --- Crypto schema (from symbol_watcher_fleet / harmonic_signal_connector) ---
            elif domain == "crypto":
                sig = {
                    "signal_id":     f"crypto|{raw.get('symbol','')}|{raw.get('signal_type','')}",
                    "domain":        "crypto",
                    "asset":         raw.get("symbol", raw.get("pair", "")),
                    "signal_type":   raw.get("signal_type", raw.get("direction", "unknown")),
                    "edge_pct":      _safe(raw.get("edge_bps", 0.0)) / 100.0,  # bps → pct
                    "best_price":    _safe(raw.get("best_price", raw.get("last", 0.0))),
                    "ref_price":     _safe(raw.get("vwap", raw.get("ref_price", 0.0))),
                    "worst_price":   _safe(raw.get("worst_price", raw.get("low", 0.0))),
                    "n_sources":     int(_safe(raw.get("n_exchanges", raw.get("n_books", 1)))),
                    "is_soft_source": False,
                    "repeat_count":  int(_safe(raw.get("repeat_count", 0))),
                    "scanned_utc":   raw.get("scanned_utc", raw.get("ts", _now_utc())),
                    "_raw":          raw,
                }

            # --- Infrastructure / cross-sector schema ---
            elif domain == "infra":
                sig = {
                    "signal_id":     f"infra|{raw.get('sector','unknown')}|{raw.get('event_id',raw.get('id',''))}",
                    "domain":        "infra",
                    "asset":         raw.get("sector", raw.get("category", "unknown")),
                    "signal_type":   raw.get("signal_type", raw.get("type", "optimization")),
                    "edge_pct":      _safe(raw.get("edge_pct", raw.get("gain_pct", 0.0))),
                    "best_price":    _safe(raw.get("best_score", raw.get("optimized_value", 0.0))),
                    "ref_price":     _safe(raw.get("baseline_score", raw.get("mean_value", 0.0))),
                    "worst_price":   _safe(raw.get("worst_score", raw.get("min_value", 0.0))),
                    "n_sources":     int(_safe(raw.get("n_sources", raw.get("n_datasets", 1)))),
                    "is_soft_source": True,
                    "repeat_count":  int(_safe(raw.get("repeat_count", 0))),
                    "scanned_utc":   raw.get("scanned_utc", raw.get("ts", _now_utc())),
                    "_raw":          raw,
                }

            # --- Digital scout / generic schema ---
            else:
                sig = {
                    "signal_id":     f"{domain}|{raw.get('id', '')}",
                    "domain":        domain,
                    "asset":         str(raw.get("asset", raw.get("target", "unknown"))),
                    "signal_type":   raw.get("signal_type", "alert"),
                    "edge_pct":      _safe(raw.get("edge_pct", raw.get("score", 0.0))),
                    "best_price":    _safe(raw.get("best_price", raw.get("value", 1.0))),
                    "ref_price":     _safe(raw.get("ref_price", raw.get("baseline", 1.0))),
                    "worst_price":   _safe(raw.get("worst_price", raw.get("min_value", 0.0))),
                    "n_sources":     int(_safe(raw.get("n_sources", 1))),
                    "is_soft_source": bool(raw.get("is_soft_source", True)),
                    "repeat_count":  int(_safe(raw.get("repeat_count", 0))),
                    "scanned_utc":   raw.get("scanned_utc", _now_utc()),
                    "_raw":          raw,
                }

            # Score it
            sig["flowform"] = score_signal(
                edge_pct=sig["edge_pct"],
                best_price=sig["best_price"],
                ref_price=sig["ref_price"],
                worst_price=sig["worst_price"],
                n_sources=sig["n_sources"],
                is_soft_source=sig["is_soft_source"],
                repeat_count=sig["repeat_count"],
                domain=domain,
            )
            self._signals.append(sig)

    def get_ranked(self, top_n: int = 50) -> List[Dict]:
        s = sorted(
            self._signals,
            key=lambda x: -x.get("flowform", {}).get("hybrid_harmonic_score", 0.0)
        )
        return s[:top_n]

    def get_by_domain(self, domain: str) -> List[Dict]:
        return [s for s in self._signals if s.get("domain") == domain]

    def domain_summary(self) -> Dict[str, Any]:
        counts: Dict[str, int] = defaultdict(int)
        top_scores: Dict[str, float] = defaultdict(float)
        for sig in self._signals:
            d = sig.get("domain", "unknown")
            counts[d] += 1
            score = sig.get("flowform", {}).get("hybrid_harmonic_score", 0.0)
            if score > top_scores[d]:
                top_scores[d] = score
        return {
            "generated_utc":  _now_utc(),
            "total_signals":  len(self._signals),
            "by_domain": {
                d: {
                    "count":     counts[d],
                    "top_score": round(top_scores[d], 4),
                }
                for d in counts
            },
        }

    def write(self) -> None:
        ranked = self.get_ranked(100)
        summary = self.domain_summary()

        _atomic_write(OUT_DIR / "_cross_domain_ranked.json", {
            "generated_utc": _now_utc(),
            "method":        "universal_harmonic_edge_core_v1",
            "phi":           PHI,
            "total":         len(self._signals),
            "summary":       summary["by_domain"],
            "top_signals":   ranked,
        })

        # Separate domain slices
        for domain in ("sports", "crypto", "infra", "digital_scout"):
            domain_sigs = self.get_by_domain(domain)
            if domain_sigs:
                domain_sigs.sort(key=lambda x: -x.get("flowform", {}).get("hybrid_harmonic_score", 0.0))
                _atomic_write(OUT_DIR / f"_{domain}_ranked.json", {
                    "generated_utc": _now_utc(),
                    "domain":        domain,
                    "count":         len(domain_sigs),
                    "signals":       domain_sigs[:50],
                })

        return summary


# ── Cross-Domain Pass: loads from existing engine outputs ────────────────────

def run_cross_domain_pass() -> Dict:
    """
    Single pass: loads outputs from all available engines, scores them
    through the universal harmonic core, writes unified ranked output.
    """
    agg = CrossDomainAggregator()

    # Sports — load from intelligence layer outputs
    sports_dir = ROOT_DIR / "out" / "sports_signals"
    for fname in ("_live_signals.json", "_arbitrage_only.json", "_value_bets.json"):
        try:
            data = json.loads((sports_dir / fname).read_text(encoding="utf-8"))
            sigs = data.get("signals", []) if isinstance(data, dict) else []
            if sigs:
                agg.ingest_signals("sports", sigs)
        except Exception:
            pass

    # Crypto — load from symbol watcher fleet if available
    fleet_dir = ROOT_DIR / "out" / "symbol_states"
    try:
        summary = json.loads((fleet_dir / "_fleet_summary.json").read_text(encoding="utf-8"))
        spikes  = json.loads((fleet_dir / "_real_spike_alerts.json").read_text(encoding="utf-8"))
        crypto_sigs = spikes if isinstance(spikes, list) else []
        if crypto_sigs:
            agg.ingest_signals("crypto", crypto_sigs)
    except Exception:
        pass

    # Infra — load from cross_sector_optimization_report if available
    try:
        report = json.loads((ROOT_DIR / "cross_sector_optimization_report.json").read_text(encoding="utf-8"))
        # extract sector signal list if it exists
        infra_sigs = report.get("sectors", report.get("results", []))
        if isinstance(infra_sigs, list) and infra_sigs:
            agg.ingest_signals("infra", infra_sigs)
    except Exception:
        pass

    summary = agg.write()
    ranked  = agg.get_ranked(5)

    ts = _now_utc()
    n  = len(agg._signals)
    top = ranked[0] if ranked else None
    top_score = top.get("flowform", {}).get("hybrid_harmonic_score", 0.0) if top else 0.0
    top_asset = top.get("asset", "-") if top else "-"
    top_domain = top.get("domain", "-") if top else "-"

    print(
        f"[UniversalHarmonicCore][{ts}] "
        f"Total={n} | Top={top_domain}:{top_asset} score={round(top_score,2)}"
    )

    if isinstance(summary, dict):
        print(f"  By domain: {summary.get('by_domain', {})}")

    return {
        "generated_utc":  ts,
        "total_signals":  n,
        "top_domain":     top_domain,
        "top_asset":      top_asset,
        "top_score":      round(top_score, 4),
    }


if __name__ == "__main__":
    result = run_cross_domain_pass()
    print(json.dumps(result, indent=2))
