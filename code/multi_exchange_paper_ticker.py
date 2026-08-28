from __future__ import annotations

import argparse
import atexit
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from execution.crypto_allocator import optimize_candidate_weights
from execution.adaptive_regime_router import route_crypto_signal
from execution.crypto_regime_controller import infer_market_regime
from execution.order_router import OrderRouter, RouteIntent
from execution.shadow_runner import ShadowRunner, ShadowFill
from execution.trade_ledger import TradeLedger
from execution.audit_chain import AuditChain
from execution.alpaca_paper_executor import (
    PAPER_TRADING_ORIGIN,
    PaperEndpointError,
    normalize_paper_trading_base,
)
import requests

try:
    import orjson
except Exception:
    orjson = None


ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).expanduser().resolve()
CODE = ROOT / "code"
CONF = ROOT / "config"
OUT = ROOT / "out" / "execution"

RUNTIME_FILE = CONF / "runtime_control.json"
STATUS_FILE = OUT / "multi_exchange_paper_ticker_status.json"
LEDGER_FILE = OUT / "multi_exchange_paper_ticker_ledger.jsonl"
BINANCEUS_PAPER_STATE_FILE = OUT / "binanceus_paper_state.json"
BINANCEUS_PAPER_LEDGER_FILE = OUT / "binanceus_paper_ledger.jsonl"
BINANCEUS_PAPER_SCOREBOARD_FILE = OUT / "binanceus_paper_scoreboard.json"
ALPACA_TRUE_PAPER_STATE_FILE = OUT / "alpaca_true_paper_state.json"
ALPACA_TRUE_PAPER_LEDGER_FILE = OUT / "alpaca_true_paper_ledger.jsonl"
INSTITUTIONAL_PAPER_REPORT_FILE = OUT / "institutional_crypto_paper_report.json"
INSTITUTIONAL_PAPER_HASH_FILE = OUT / "institutional_crypto_paper_report_sha256.json"
INSTITUTIONAL_PAPER_DASHBOARD_FILE = ROOT / "dashboard" / "institutional_crypto_paper_dashboard.html"
INSTITUTIONAL_PAPER_BRIEF_FILE = OUT / "institutional_crypto_executive_brief.pdf"
LOCK_FILE = CODE / ".multi_exchange_paper_ticker.lock"
DUCKDB_KPI_FILE = OUT / "analytics" / "investor_kpi_duckdb.json"
ROLLING_BEST_FILE = Path(
    os.environ.get(
        "LUMA_ROLLING_CAPITAL_FILE",
        str(ROOT.parent / "rolling_capital" / "rolling_capital_best_multi.json"),
    )
).expanduser()
EXECUTION_AUDIT_CHAIN_FILE = OUT / "execution_audit_chain.jsonl"
INVESTOR_SCORECARD_FILE = OUT / "investor_proof_scorecard.json"
INVESTOR_SCORECARD_HISTORY_FILE = OUT / "investor_proof_scorecard.jsonl"
TRADE_LEDGER_CSV_FILE = OUT / "multi_exchange_trade_ledger.csv"
TRADE_LEDGER_JSONL_FILE = OUT / "multi_exchange_trade_ledger.jsonl"
SHADOW_LEDGER_CSV_FILE = OUT / "multi_exchange_shadow_fills.csv"

_LAST_BINANCEUS_PRIVATE_SNAPSHOT: Dict[str, Any] | None = None
_LAST_BINANCEUS_PRIVATE_FETCH_TS: float = 0.0

DEFAULT_PROFILE = "apex"
PROFILE_PRESETS: Dict[str, Dict[str, Any]] = {
    "hybrid": {
        "max_positions": 6,
        "max_scan_symbols": 300,
        "base_risk_fraction": 0.07,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.22,
        "max_gross_heat_pct": 0.70,
        "target_position_vol_pct": 0.035,
        "uncertainty_penalty_k": 1.20,
        "min_diversified_slots": 4,
        "vol_scalar_floor": 0.45,
        "vol_scalar_ceiling": 1.20,
        "moon_trigger": 0.014,
        "entry_min_notional_usd": 30.0,
        "entry_max_risk_fraction": 0.22,
        "tp_moon": 0.018,
        "tp_fallback": 0.010,
        "sl": -0.007,
        "timeout_cycles": 12,
        "hybrid_weight_base": 0.58,
        "hybrid_weight_breadth_k": 0.30,
        "min_edge": 0.04,
        "min_pct24": 0.03,
        "min_quote_volume_usd": 150.0,
    },
    "advanced": {
        "max_positions": 8,
        "max_scan_symbols": 500,
        "base_risk_fraction": 0.085,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.20,
        "max_gross_heat_pct": 0.72,
        "target_position_vol_pct": 0.038,
        "uncertainty_penalty_k": 1.15,
        "min_diversified_slots": 5,
        "vol_scalar_floor": 0.45,
        "vol_scalar_ceiling": 1.22,
        "moon_trigger": 0.010,
        "entry_min_notional_usd": 40.0,
        "entry_max_risk_fraction": 0.24,
        "tp_moon": 0.022,
        "tp_fallback": 0.012,
        "sl": -0.008,
        "timeout_cycles": 16,
        "hybrid_weight_base": 0.64,
        "hybrid_weight_breadth_k": 0.45,
        "min_edge": 0.05,
        "min_pct24": 0.04,
        "min_quote_volume_usd": 250.0,
    },
    "hyperfire": {
        "max_positions": 10,
        "max_scan_symbols": 700,
        "base_risk_fraction": 0.16,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.18,
        "max_gross_heat_pct": 0.78,
        "target_position_vol_pct": 0.045,
        "uncertainty_penalty_k": 1.00,
        "min_diversified_slots": 6,
        "vol_scalar_floor": 0.40,
        "vol_scalar_ceiling": 1.25,
        "moon_trigger": 0.004,
        "entry_min_notional_usd": 20.0,
        "entry_max_risk_fraction": 0.30,
        "tp_moon": 0.008,
        "tp_fallback": 0.005,
        "sl": -0.010,
        "timeout_cycles": 1,
        "hybrid_weight_base": 0.70,
        "hybrid_weight_breadth_k": 0.55,
        "min_edge": 0.07,
        "min_pct24": 0.08,
        "min_quote_volume_usd": 500.0,
    },
    "apex": {
        "max_positions": 12,
        "max_scan_symbols": 2500,
        "base_risk_fraction": 0.30,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.16,
        "max_gross_heat_pct": 0.82,
        "target_position_vol_pct": 0.050,
        "uncertainty_penalty_k": 0.95,
        "min_diversified_slots": 8,
        "vol_scalar_floor": 0.35,
        "vol_scalar_ceiling": 1.25,
        "moon_trigger": 0.003,
        "entry_min_notional_usd": 25.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.010,
        "tp_fallback": 0.006,
        "sl": -0.012,
        "timeout_cycles": 1,
        "hybrid_weight_base": 0.78,
        "hybrid_weight_breadth_k": 0.60,
        "min_edge": 0.08,
        "min_pct24": 0.10,
        "min_quote_volume_usd": 1200.0,
        "entry_mode": "capital_ladder",
        "ladder_edge_tier1": 0.22,
        "ladder_frac_tier1": 0.55,
        "ladder_edge_tier2": 0.16,
        "ladder_frac_tier2": 0.32,
        "ladder_edge_tier3": 0.10,
        "ladder_frac_tier3": 0.18,
        "ladder_frac_floor": 0.06,
        "ladder_top1_frac": 0.55,
        "ladder_top2_frac": 0.28,
    },
    # ── BREAKOUT ─────────────────────────────────────────────────────────────────
    # Detects coins sitting near 24h high with accelerating trade density.
    # Fires BEFORE the blow-off, not after. Low volume floor kept high enough
    # to have an exit. Chase penalty kills anything already up >30%.
    "breakout": {
        "max_positions": 6,
        "max_scan_symbols": 800,
        "base_risk_fraction": 0.35,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.18,
        "max_gross_heat_pct": 0.74,
        "target_position_vol_pct": 0.042,
        "uncertainty_penalty_k": 1.05,
        "min_diversified_slots": 4,
        "vol_scalar_floor": 0.40,
        "vol_scalar_ceiling": 1.20,
        "moon_trigger": 0.002,
        "entry_min_notional_usd": 50.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.018,
        "tp_fallback": 0.010,
        "sl": -0.009,
        "timeout_cycles": 4,
        "hybrid_weight_base": 0.88,
        "hybrid_weight_breadth_k": 0.40,
        "min_edge": 0.09,
        "min_pct24": 0.0,
        "max_pct24": 0.30,
        "min_quote_volume_usd": 250.0,
        "min_near_high": 0.75,
        "min_r2": 0.0005,
        "reentry_cooldown_cycles": 8,
        "entry_mode": "capital_ladder",
        "score_regime": "breakout",
        "ladder_edge_tier1": 0.28,
        "ladder_frac_tier1": 0.58,
        "ladder_edge_tier2": 0.18,
        "ladder_frac_tier2": 0.34,
        "ladder_edge_tier3": 0.10,
        "ladder_frac_tier3": 0.20,
        "ladder_frac_floor": 0.08,
        "ladder_top1_frac": 0.58,
        "ladder_top2_frac": 0.30,
    },
    "triplet": {
        "max_positions": 12,
        "max_scan_symbols": 2500,
        "base_risk_fraction": 0.28,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.16,
        "max_gross_heat_pct": 0.85,
        "target_position_vol_pct": 0.050,
        "uncertainty_penalty_k": 0.95,
        "min_diversified_slots": 8,
        "vol_scalar_floor": 0.35,
        "vol_scalar_ceiling": 1.25,
        "moon_trigger": 0.003,
        "entry_min_notional_usd": 25.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.010,
        "tp_fallback": 0.006,
        "tp_breakout": 0.014,
        "sl": -0.012,
        "timeout_cycles": 1,
        "hybrid_weight_base": 0.78,
        "hybrid_weight_breadth_k": 0.60,
        "min_edge": 0.08,
        "min_pct24": 0.05,
        "min_quote_volume_usd": 1000.0,
        "entry_mode": "capital_ladder",
        "ladder_edge_tier1": 0.22,
        "ladder_frac_tier1": 0.55,
        "ladder_edge_tier2": 0.16,
        "ladder_frac_tier2": 0.32,
        "ladder_edge_tier3": 0.10,
        "ladder_frac_tier3": 0.18,
        "ladder_frac_floor": 0.06,
        "ladder_top1_frac": 0.55,
        "ladder_top2_frac": 0.28,
        "engine_mode": "triplet",
        "triplet_slots_breakout": 4,
        "triplet_slots_moon": 4,
        "triplet_slots_fallback": 4,
        "triplet_breakout_cap_pct": 0.45,
        "triplet_moon_cap_pct": 0.35,
        "triplet_fallback_cap_pct": 0.20,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # LUMEN HARMONIC FIBONACCI INSTITUTIONAL SUITE
    # φ = 1.6180339887  (golden ratio)
    # Capital ladder fracs → pure Fibonacci: [0.618, 0.382, 0.236]
    # Edge tiers → φ-geometric series: 0.250 → 0.154 → 0.095
    # TP moon = entry_risk × φ  |  TP fallback = entry_risk × 1.0  |  SL = -risk × 0.382
    # Gross heat cap = φ / 2 = 0.809 (golden deployment ceiling)
    # ══════════════════════════════════════════════════════════════════════════════

    # ── RENPARITY ────────────────────────────────────────────────────────────────
    # Renaissance Medallion × Lumen Harmonic
    # Philosophy: stat-arb breadth — scan the widest possible market, size every
    # signal by its vol-adjusted edge weight, rotate positions every cycle.
    # Lumen upgrade: Fibonacci-scaled ladder fracs, φ-spaced edge tiers, any signal
    # with edge > floor gets a proportional crumb rather than being cut out entirely.
    "renparity": {
        "max_positions": 14,
        "max_scan_symbols": 2500,
        "base_risk_fraction": 0.22,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.12,
        "max_gross_heat_pct": 0.809,           # φ / 2
        "target_position_vol_pct": 0.030,
        "uncertainty_penalty_k": 1.00,
        "min_diversified_slots": 10,
        "vol_scalar_floor": 0.382,             # Fibonacci 0.382 — natural vol floor
        "vol_scalar_ceiling": 1.618,           # φ — natural vol ceiling
        "moon_trigger": 0.002,
        "entry_min_notional_usd": 15.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.016,                      # 0.010 × φ
        "tp_fallback": 0.010,
        "sl": -0.006,                          # -0.010 × 0.618 (Fibonacci SL)
        "timeout_cycles": 1,                   # Medallion-style: high turnover
        "hybrid_weight_base": 0.62,
        "hybrid_weight_breadth_k": 0.618,      # φ-inverse breadth kernel
        "min_edge": 0.045,
        "min_pct24": 0.005,
        "min_quote_volume_usd": 500.0,
        "entry_mode": "capital_ladder",
        "ladder_edge_tier1": 0.250,            # φ-spaced: 0.095 × φ² ≈ 0.250
        "ladder_frac_tier1": 0.618,            # Fibonacci primary fraction
        "ladder_edge_tier2": 0.154,            # 0.250 / φ
        "ladder_frac_tier2": 0.382,            # Fibonacci secondary
        "ladder_edge_tier3": 0.095,            # 0.154 / φ
        "ladder_frac_tier3": 0.236,            # Fibonacci tertiary
        "ladder_frac_floor": 0.090,
        "ladder_top1_frac": 0.618,
        "ladder_top2_frac": 0.382,
        "lumen_harmonic": True,
    },

    # ── TIGER ─────────────────────────────────────────────────────────────────────
    # Tiger Global / Coatue concentrated conviction × Lumen Harmonic
    # Philosophy: max 4 slots, enormous per-slot sizing, hold for the home-run move.
    # Only fire when edge clears the φ² = 2.618 threshold implied by minimum bar.
    # R:R = 1 : φ² (risk 1 unit to make 2.618 units — full golden extension target).
    "tiger": {
        "max_positions": 4,
        "max_scan_symbols": 1200,
        "base_risk_fraction": 0.50,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.35,
        "max_gross_heat_pct": 0.809,
        "target_position_vol_pct": 0.065,
        "uncertainty_penalty_k": 0.88,
        "min_diversified_slots": 2,
        "vol_scalar_floor": 0.382,
        "vol_scalar_ceiling": 1.618,
        "moon_trigger": 0.001,
        "entry_min_notional_usd": 80.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.026,                      # 0.010 × φ² = 0.010 × 2.618
        "tp_fallback": 0.016,                  # 0.010 × φ
        "sl": -0.010,                          # R:R = 2.618 on moon leg
        "timeout_cycles": 48,                  # Patience — Tiger holds
        "hybrid_weight_base": 0.85,
        "hybrid_weight_breadth_k": 0.382,
        "min_edge": 0.18,                      # High conviction gate
        "min_pct24": 0.02,
        "min_quote_volume_usd": 2000.0,
        "entry_mode": "capital_ladder",
        "ladder_edge_tier1": 0.382,            # Only the top Fibonacci level fires tier1
        "ladder_frac_tier1": 0.618,
        "ladder_edge_tier2": 0.236,
        "ladder_frac_tier2": 0.382,
        "ladder_edge_tier3": 0.146,            # 0.236 / φ
        "ladder_frac_tier3": 0.236,
        "ladder_frac_floor": 0.118,
        "ladder_top1_frac": 0.618,
        "ladder_top2_frac": 0.382,
        "lumen_harmonic": True,
    },

    # ── CITPOD_LUMEN ─────────────────────────────────────────────────────────────
    # Citadel multi-pod × Lumen Harmonic
    # Runs 4 engine pods simultaneously; capital routed by Fibonacci weight:
    #   breakout=0.382 | moon=0.309 (0.382/φ) | fallback=0.191 | carry=0.118
    # Each pod fires independently so single-regime washouts don't collapse the book.
    "citpod_lumen": {
        "max_positions": 16,
        "max_scan_symbols": 2500,
        "base_risk_fraction": 0.32,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.14,
        "max_gross_heat_pct": 0.809,
        "target_position_vol_pct": 0.048,
        "uncertainty_penalty_k": 0.95,
        "min_diversified_slots": 10,
        "vol_scalar_floor": 0.382,
        "vol_scalar_ceiling": 1.618,
        "moon_trigger": 0.002,
        "entry_min_notional_usd": 20.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.016,
        "tp_fallback": 0.010,
        "tp_breakout": 0.022,
        "sl": -0.008,
        "timeout_cycles": 2,
        "hybrid_weight_base": 0.76,
        "hybrid_weight_breadth_k": 0.618,
        "min_edge": 0.07,
        "min_pct24": 0.02,
        "min_near_high": 0.618,               # Breakout pod: near-high Fibonacci gate
        "min_quote_volume_usd": 800.0,
        "entry_mode": "capital_ladder",
        "ladder_edge_tier1": 0.250,
        "ladder_frac_tier1": 0.618,
        "ladder_edge_tier2": 0.154,
        "ladder_frac_tier2": 0.382,
        "ladder_edge_tier3": 0.095,
        "ladder_frac_tier3": 0.236,
        "ladder_frac_floor": 0.090,
        "ladder_top1_frac": 0.618,
        "ladder_top2_frac": 0.382,
        "engine_mode": "triplet",
        "triplet_slots_breakout": 6,           # φ-weighted: 6 / 4 / 4 / 2 ≈ fib
        "triplet_slots_moon": 6,
        "triplet_slots_fallback": 4,
        "triplet_breakout_cap_pct": 0.382,     # Fibonacci pod capital
        "triplet_moon_cap_pct": 0.382,
        "triplet_fallback_cap_pct": 0.236,
        "lumen_harmonic": True,
    },

    # ── ALLWEATHER_LUMEN ─────────────────────────────────────────────────────────
    # Bridgewater All Weather × Lumen Harmonic
    # Philosophy: risk parity — every slot contributes the SAME volatility budget.
    # Achieved here via tighter vol targeting + Fibonacci-scaled per-regime heat.
    # In defensive regime: heat scales to φ⁻² = 0.382 of normal.
    # In expansion regime: heat scales to φ = 1.618 (capped at max_gross_heat).
    "allweather_lumen": {
        "max_positions": 10,
        "max_scan_symbols": 1500,
        "base_risk_fraction": 0.18,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.15,
        "max_gross_heat_pct": 0.809,
        "target_position_vol_pct": 0.025,      # Tight vol-targeting: equal risk units
        "uncertainty_penalty_k": 1.10,
        "min_diversified_slots": 7,
        "vol_scalar_floor": 0.382,
        "vol_scalar_ceiling": 1.618,
        "moon_trigger": 0.004,
        "entry_min_notional_usd": 30.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.016,                      # 1R × φ
        "tp_fallback": 0.010,
        "sl": -0.006,                          # 1R × 0.618 (Golden SL)
        "timeout_cycles": 8,
        "hybrid_weight_base": 0.65,
        "hybrid_weight_breadth_k": 0.500,
        "min_edge": 0.06,
        "min_pct24": 0.0,                      # All-weather includes slight pullbacks
        "min_quote_volume_usd": 400.0,
        "entry_mode": "capital_ladder",
        "ladder_edge_tier1": 0.250,
        "ladder_frac_tier1": 0.618,
        "ladder_edge_tier2": 0.154,
        "ladder_frac_tier2": 0.382,
        "ladder_edge_tier3": 0.095,
        "ladder_frac_tier3": 0.236,
        "ladder_frac_floor": 0.090,
        "ladder_top1_frac": 0.618,
        "ladder_top2_frac": 0.382,
        "lumen_harmonic": True,
    },

    # ── AQR_FACTOR ────────────────────────────────────────────────────────────────
    # AQR Multi-Factor × Lumen Harmonic
    # Philosophy: score candidates on 3 rolled factors simultaneously:
    #   (1) momentum (r2/r4/r8 composite)
    #   (2) market quality (trade_density × quote_vol normalised)
    #   (3) breadth participation (pct24 vs universe median)
    # Fibonacci breadth thresholds: expansion ≥ 0.618, defensive ≤ 0.382.
    # Medium concentration, market-neutral framing (min_pct24 slightly negative
    # to include mean-reversion setups alongside trend).
    "aqr_factor": {
        "max_positions": 10,
        "max_scan_symbols": 2000,
        "base_risk_fraction": 0.25,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.15,
        "max_gross_heat_pct": 0.809,
        "target_position_vol_pct": 0.040,
        "uncertainty_penalty_k": 1.05,
        "min_diversified_slots": 7,
        "vol_scalar_floor": 0.382,
        "vol_scalar_ceiling": 1.618,
        "moon_trigger": 0.003,
        "entry_min_notional_usd": 30.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.016,
        "tp_fallback": 0.010,
        "sl": -0.007,
        "timeout_cycles": 6,
        "hybrid_weight_base": 0.72,
        "hybrid_weight_breadth_k": 0.618,
        "min_edge": 0.06,
        "min_pct24": -0.02,                    # AQR: include slight reversions
        "min_quote_volume_usd": 600.0,
        "entry_mode": "capital_ladder",
        "ladder_edge_tier1": 0.250,
        "ladder_frac_tier1": 0.618,
        "ladder_edge_tier2": 0.154,
        "ladder_frac_tier2": 0.382,
        "ladder_edge_tier3": 0.095,
        "ladder_frac_tier3": 0.236,
        "ladder_frac_floor": 0.090,
        "ladder_top1_frac": 0.618,
        "ladder_top2_frac": 0.382,
        "lumen_harmonic": True,
    },

    # ── MILLENNIUM_GATE ───────────────────────────────────────────────────────────
    # Point72 / Millennium catalyst-gated × Lumen Harmonic
    # Philosophy: only trade when near-breakout catalyst exists AND breadth confirms.
    # Strict reentry cooldown prevents chasing the echo.
    # Fibonacci catalyst gate: near_high ≥ 0.618 required before any entry.
    # Strict SL at Fibonacci 0.236 of range (tightest of all profiles).
    "millennium_gate": {
        "max_positions": 8,
        "max_scan_symbols": 1800,
        "base_risk_fraction": 0.28,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.18,
        "max_gross_heat_pct": 0.809,
        "target_position_vol_pct": 0.042,
        "uncertainty_penalty_k": 1.08,
        "min_diversified_slots": 5,
        "vol_scalar_floor": 0.382,
        "vol_scalar_ceiling": 1.618,
        "moon_trigger": 0.002,
        "entry_min_notional_usd": 40.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.022,
        "tp_fallback": 0.013,
        "sl": -0.008,
        "timeout_cycles": 5,
        "hybrid_weight_base": 0.82,
        "hybrid_weight_breadth_k": 0.500,
        "min_edge": 0.10,
        "min_pct24": 0.01,
        "min_near_high": 0.618,               # Fibonacci catalyst gate
        "min_r2": 0.0003,
        "min_quote_volume_usd": 800.0,
        "reentry_cooldown_cycles": 13,        # Fibonacci number cooldown
        "entry_mode": "capital_ladder",
        "score_regime": "breakout",
        "ladder_edge_tier1": 0.250,
        "ladder_frac_tier1": 0.618,
        "ladder_edge_tier2": 0.154,
        "ladder_frac_tier2": 0.382,
        "ladder_edge_tier3": 0.095,
        "ladder_frac_tier3": 0.236,
        "ladder_frac_floor": 0.090,
        "ladder_top1_frac": 0.618,
        "ladder_top2_frac": 0.382,
        "lumen_harmonic": True,
    },
    "lumenstyle": {
        "max_positions": 14,
        "max_scan_symbols": 3000,
        "base_risk_fraction": 0.34,
        "allocator_mode": "scientific_hybrid",
        "max_single_position_pct": 0.20,
        "max_gross_heat_pct": 0.86,
        "target_position_vol_pct": 0.050,
        "uncertainty_penalty_k": 0.92,
        "min_diversified_slots": 9,
        "vol_scalar_floor": 0.30,
        "vol_scalar_ceiling": 1.30,
        "moon_trigger": 0.003,
        "entry_min_notional_usd": 20.0,
        "entry_max_risk_fraction": 1.00,
        "tp_moon": 0.012,
        "tp_fallback": 0.007,
        "tp_dislocation": 0.040,
        "sl": -0.013,
        "timeout_cycles": 2,
        "hybrid_weight_base": 0.76,
        "hybrid_weight_breadth_k": 0.55,
        "dislocation_weight": 0.35,
        "min_edge": 0.08,
        "min_dislocation_score": 0.12,
        "min_pct24": 0.00,
        "min_quote_volume_usd": 900.0,
        "entry_mode": "capital_ladder",
        "ladder_edge_tier1": 0.24,
        "ladder_frac_tier1": 0.60,
        "ladder_edge_tier2": 0.16,
        "ladder_frac_tier2": 0.35,
        "ladder_edge_tier3": 0.10,
        "ladder_frac_tier3": 0.20,
        "ladder_frac_floor": 0.08,
        "ladder_top1_frac": 0.60,
        "ladder_top2_frac": 0.30,
        "maker_fee_bps": 6.0,
        "taker_fee_bps": 12.0,
        "slippage_bps": 8.0,
    },
    "lumenstradigy": {
        # ── Capacity ──────────────────────────────────────────────────────────
        "max_positions": 20,           # up from 12 — wide portfolio
        "max_scan_symbols": 4000,
        "base_risk_fraction": 0.40,
        "allocator_mode": "scientific_hybrid",
        # ── Per-slot & heat caps ───────────────────────────────────────────────
        # Wide window: engine picks size inside [floor → ceiling] driven by signal
        "max_single_position_pct": 0.45,   # any single position up to 45 % of equity
        "max_gross_heat_pct": 0.98,         # can deploy nearly all capital
        # ── Vol / uncertainty scalars ─────────────────────────────────────────
        "target_position_vol_pct": 0.055,
        "uncertainty_penalty_k": 0.40,     # much softer — don't punish vol hard
        "min_diversified_slots": 3,
        "vol_scalar_floor": 0.08,           # tiny floor — small signals get small size
        "vol_scalar_ceiling": 3.00,         # strong signals can 3× their base size
        # ── Entry logic ───────────────────────────────────────────────────────
        "moon_trigger": 0.0015,
        "entry_min_notional_usd": 25.0,
        "entry_max_risk_fraction": 1.00,
        # ── Take-profit / stop / timeout ──────────────────────────────────────
        "tp_moon": 0.020,
        "tp_fallback": 0.009,
        "tp_dislocation": 0.090,
        "sl": -0.020,
        "timeout_cycles": 6,
        # ── Scoring weights ───────────────────────────────────────────────────
        "hybrid_weight_base": 0.70,
        "hybrid_weight_breadth_k": 0.40,
        "dislocation_weight": 0.60,
        "min_edge": 0.06,
        "min_dislocation_score": 0.08,
        "min_pct24": -0.99,
        "max_pct24": 0.90,
        "min_quote_volume_usd": 200.0,
        # ── Capital ladder: wide floor-to-ceiling window ─────────────────────
        # The signal_quality multiplier (vol × uncertainty × confidence) will
        # push actual notional anywhere from ~floor to ceiling based on signals.
        "entry_mode": "capital_ladder",
        "score_regime": "dislocation",
        "scan_boost": 1.25,
        "aggression_boost": 1.20,
        "ladder_edge_tier1": 0.22,          # tier edges lowered so more qualify
        "ladder_frac_tier1": 0.75,          # baseline 75 % of cash for tier-1
        "ladder_edge_tier2": 0.14,
        "ladder_frac_tier2": 0.55,
        "ladder_edge_tier3": 0.08,
        "ladder_frac_tier3": 0.35,
        "ladder_frac_floor": 0.04,          # even weak signals get 4 % — don't skip
        "ladder_top1_frac": 0.80,           # rank-1 pick baseline 80 %
        "ladder_top2_frac": 0.60,
        "ladder_frac_ceiling": 0.90,        # signal×quality can push up to 90 %
        "maker_fee_bps": 5.0,
        "taker_fee_bps": 10.0,
        "slippage_bps": 10.0,
    },
}

KEY_PATHS = [
    CONF / "luma_live_keys.env",
    CONF / "live_keys.env",
    CONF / "keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "live_keys.env",
    ROOT / "code" / "execution" / "config" / "keys.env",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            out = (proc.stdout or "").strip().lower()
            if not out or "no tasks are running" in out:
                return False
            return str(pid) in out
        except Exception:
            return False

    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except Exception:
        return False


def acquire_single_instance_lock(profile: str) -> tuple[bool, str]:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "started_utc": now_utc(),
        "script": "multi_exchange_paper_ticker.py",
        "profile": profile,
    }

    # Atomic create prevents race conditions between concurrent launches.
    def _try_create() -> tuple[bool, str]:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        fd = os.open(str(LOCK_FILE), flags)
        try:
            os.write(fd, json.dumps(payload, indent=2).encode("utf-8"))
        finally:
            os.close(fd)
        return True, "acquired"

    try:
        return _try_create()
    except FileExistsError:
        pass
    except Exception as exc:
        return False, f"lock_create_error={exc}"

    try:
        existing = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        existing_pid = int(existing.get("pid", 0))
    except Exception:
        existing_pid = 0

    if _pid_is_alive(existing_pid):
        return False, f"existing_pid={existing_pid}"

    try:
        LOCK_FILE.unlink()
    except Exception:
        return False, "stale_lock_unremovable"

    try:
        return _try_create()
    except FileExistsError:
        return False, "race_lost"
    except Exception as exc:
        return False, f"lock_recreate_error={exc}"


def release_single_instance_lock() -> None:
    try:
        if not LOCK_FILE.exists():
            return
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        if int(data.get("pid", 0)) == os.getpid():
            LOCK_FILE.unlink()
    except Exception:
        pass


def is_current_lock_owner() -> bool:
    try:
        if not LOCK_FILE.exists():
            return False
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        return int(data.get("pid", 0)) == os.getpid()
    except Exception:
        return False


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            if orjson is not None:
                return orjson.loads(path.read_bytes())
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if orjson is not None:
        path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
    else:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        if orjson is not None:
            f.write(orjson.dumps(payload).decode("utf-8") + "\n")
        else:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            row = raw.strip()
            if not row or row.startswith("#") or "=" not in row:
                continue
            key, value = row.split("=", 1)
            out[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        return {}
    return out


def hydrate_live_keys() -> Dict[str, Any]:
    hydrated = []
    source = None
    for path in KEY_PATHS:
        env = load_env_file(path)
        if not env:
            continue
        source = str(path)
        for key, value in env.items():
            if value and not os.getenv(key, "").strip():
                os.environ[key] = value
                hydrated.append(key)
        if hydrated:
            break
    return {
        "source": source,
        "hydrated_count": len(hydrated),
        "hydrated_keys": sorted(hydrated),
    }


def force_paper_mode() -> Dict[str, Any]:
    runtime = load_json(RUNTIME_FILE, {})
    before_mode = runtime.get("mode")
    before_live = runtime.get("allow_live_orders")

    runtime["mode"] = "paper"
    runtime["allow_live_orders"] = False
    runtime.setdefault("paper_enabled", True)
    save_json(RUNTIME_FILE, runtime)

    return {
        "before_mode": before_mode,
        "before_allow_live_orders": before_live,
        "after_mode": runtime.get("mode"),
        "after_allow_live_orders": runtime.get("allow_live_orders"),
    }


def _get(url: str, timeout: int = 10, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return {"ok": True, "status": resp.status_code, "data": resp.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _binance_sign(params: Dict[str, Any], secret: str) -> str:
    query = urllib.parse.urlencode(params)
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def _binanceus_private_poll_seconds() -> float:
    runtime = load_json(RUNTIME_FILE, {})
    try:
        value = float(runtime.get("binanceus_private_poll_seconds", 3.0) or 3.0)
    except Exception:
        value = 3.0
    return max(0.5, min(30.0, value))


def kraken_snapshot() -> Dict[str, Any]:
    res = _get("https://api.kraken.com/0/public/Ticker", params={"pair": "XBTUSD"}, timeout=10)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error")}
    data = res.get("data", {})
    result = data.get("result", {}) if isinstance(data, dict) else {}
    if not result:
        return {"ok": False, "error": "No result from Kraken"}
    first_key = next(iter(result.keys()))
    row = result.get(first_key, {})
    price = None
    if isinstance(row, dict):
        c = row.get("c")
        if isinstance(c, list) and c:
            try:
                price = float(c[0])
            except Exception:
                price = None
    return {"ok": True, "pair": "XBT/USD", "price": price}


def binance_snapshot(api_url: str) -> Dict[str, Any]:
    res = _get(f"{api_url}/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=10)
    if not res.get("ok"):
        return {"ok": False, "api_url": api_url, "error": res.get("error")}
    row = res.get("data", {})
    price = None
    try:
        price = float(row.get("price"))
    except Exception:
        pass
    return {"ok": True, "api_url": api_url, "symbol": "BTCUSDT", "price": price}


def binanceus_private_account_snapshot() -> Dict[str, Any]:
    global _LAST_BINANCEUS_PRIVATE_SNAPSHOT
    global _LAST_BINANCEUS_PRIVATE_FETCH_TS

    min_poll_seconds = _binanceus_private_poll_seconds()
    now_ts = time.time()
    if _LAST_BINANCEUS_PRIVATE_SNAPSHOT is not None and (now_ts - _LAST_BINANCEUS_PRIVATE_FETCH_TS) < min_poll_seconds:
        cached = dict(_LAST_BINANCEUS_PRIVATE_SNAPSHOT)
        cached["cached"] = True
        cached["cache_age_sec"] = round(now_ts - _LAST_BINANCEUS_PRIVATE_FETCH_TS, 3)
        cached["min_poll_seconds"] = min_poll_seconds
        return cached

    key = os.getenv("BINANCE_API_KEY", "").strip()
    secret = os.getenv("BINANCE_API_SECRET", "").strip()
    api_url = "https://api.binance.us"

    if not key or not secret:
        payload = {
            "ok": False,
            "api_url": api_url,
            "error": "Missing BINANCE_API_KEY/BINANCE_API_SECRET",
            "min_poll_seconds": min_poll_seconds,
        }
        _LAST_BINANCEUS_PRIVATE_FETCH_TS = now_ts
        _LAST_BINANCEUS_PRIVATE_SNAPSHOT = dict(payload)
        return payload

    params: Dict[str, Any] = {
        "timestamp": int(time.time() * 1000),
        "recvWindow": 5000,
    }
    params["signature"] = _binance_sign(params, secret)
    headers = {"X-MBX-APIKEY": key}

    try:
        resp = requests.get(f"{api_url}/api/v3/account", params=params, headers=headers, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        balances = data.get("balances", []) if isinstance(data, dict) else []
        nonzero = []
        for row in balances:
            try:
                free = float(row.get("free", 0.0))
                locked = float(row.get("locked", 0.0))
            except Exception:
                continue
            if abs(free) > 0 or abs(locked) > 0:
                nonzero.append(
                    {
                        "asset": row.get("asset"),
                        "free": free,
                        "locked": locked,
                    }
                )
        payload = {
            "ok": True,
            "api_url": api_url,
            "can_trade": bool(data.get("canTrade", False)),
            "account_type": data.get("accountType"),
            "nonzero_balances": nonzero[:12],
            "nonzero_balance_count": len(nonzero),
            "cached": False,
            "min_poll_seconds": min_poll_seconds,
        }
        _LAST_BINANCEUS_PRIVATE_FETCH_TS = now_ts
        _LAST_BINANCEUS_PRIVATE_SNAPSHOT = dict(payload)
        return payload
    except Exception as exc:
        payload = {
            "ok": False,
            "api_url": api_url,
            "error": str(exc),
            "cached": False,
            "min_poll_seconds": min_poll_seconds,
        }
        _LAST_BINANCEUS_PRIVATE_FETCH_TS = now_ts
        _LAST_BINANCEUS_PRIVATE_SNAPSHOT = dict(payload)
        return payload


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _i(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _execution_friction_rates(preset: Dict[str, Any]) -> Dict[str, float]:
    taker_bps = min(max(_f(preset.get("taker_fee_bps"), 10.0), 0.0), 100.0)
    maker_bps = min(max(_f(preset.get("maker_fee_bps"), max(taker_bps * 0.6, 0.0)), 0.0), 100.0)
    slippage_bps = min(max(_f(preset.get("slippage_bps"), 8.0), 0.0), 200.0)
    return {
        "maker_fee_rate": maker_bps / 10_000.0,
        "taker_fee_rate": taker_bps / 10_000.0,
        "slippage_rate": slippage_bps / 10_000.0,
        "maker_fee_bps": maker_bps,
        "taker_fee_bps": taker_bps,
        "slippage_bps": slippage_bps,
    }


def _load_external_intel() -> Dict[str, Any]:
    kpi = load_json(DUCKDB_KPI_FILE, {})
    rolling_best = load_json(ROLLING_BEST_FILE, {})

    risk_multiplier = 1.0
    scan_multiplier = 1.0

    if isinstance(kpi, dict) and kpi:
        sample_tier = str(kpi.get("sample_quality_tier", "")).lower()
        sharpe_proxy = _f(kpi.get("sharpe_proxy"), 0.0)
        avg_fee_drag_pct = _f(kpi.get("avg_fee_drag_pct_per_trade"), 0.0)
        max_drawdown = _f(kpi.get("max_drawdown"), 0.0)

        if sample_tier in {"institutional", "pilot"} and sharpe_proxy >= 1.0:
            risk_multiplier *= 1.05
            scan_multiplier *= 1.05
        elif sample_tier == "insufficient" or sharpe_proxy < 0.0:
            risk_multiplier *= 0.90

        if avg_fee_drag_pct >= 0.25:
            risk_multiplier *= 0.88
            scan_multiplier *= 0.95
        elif avg_fee_drag_pct >= 0.15:
            risk_multiplier *= 0.94

        if max_drawdown <= -0.25:
            risk_multiplier *= 0.85
        elif max_drawdown <= -0.15:
            risk_multiplier *= 0.92

    preferred_regime = ""
    preferred_family = ""
    preferred_symbol = ""
    if isinstance(rolling_best, dict) and rolling_best:
        preferred_family = str(rolling_best.get("family", "")).lower()
        preferred_symbol = str(rolling_best.get("symbol", "")).upper().replace("/", "")
        if preferred_family in {"breakout_pressure", "torsion_trend"}:
            preferred_regime = "breakout"
            scan_multiplier *= 1.08
        elif preferred_family in {"momentum_lowvol", "harmonic_hybrid", "helix_cycle"}:
            preferred_regime = "moonshot"
            scan_multiplier *= 1.06
        elif preferred_family in {"dispersion_harvest", "fractal_balance"}:
            preferred_regime = "fallback"
            scan_multiplier *= 1.04

    return {
        "risk_multiplier": min(max(risk_multiplier, 0.70), 1.20),
        "scan_multiplier": min(max(scan_multiplier, 0.85), 1.25),
        "preferred_regime": preferred_regime,
        "preferred_family": preferred_family,
        "preferred_symbol": preferred_symbol,
        "kpi": kpi if isinstance(kpi, dict) else {},
        "rolling_best": rolling_best if isinstance(rolling_best, dict) else {},
    }


def _infer_dislocation_reason(pct24: float, near_high: float, r2: float, accel: float, trade_density: float) -> str:
    if pct24 <= -0.70 and near_high <= 0.15:
        return "probable_liquidation_cascade_or_bad_tick"
    if pct24 <= -0.40 and trade_density >= 0.55:
        return "panic_selloff_with_liquidity_spike"
    if pct24 <= -0.25 and r2 > 0.01 and accel > 0:
        return "v_reversal_after_shock"
    if pct24 <= -0.15 and near_high < 0.35:
        return "oversold_drawdown_reversion_setup"
    return "momentum_reversion_candidate"


def _resolve_urgency(edge: float, trade_density: float, accel: float, route: str) -> str:
    if route == "maker":
        return "passive"
    if edge >= 0.20 or trade_density >= 0.65 or accel >= 0.02:
        return "aggressive"
    return "normal"


def _binanceus_24h_snapshot() -> Dict[str, Any]:
    url = "https://api.binance.us/api/v3/ticker/24hr"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        rows = resp.json()
        if not isinstance(rows, list):
            return {"ok": False, "error": "Unexpected payload"}
        return {"ok": True, "rows": rows}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _kraken_symbol_to_usd_pair(raw: str) -> str:
    sym = str(raw or "").upper().replace("/", "").replace("-", "").replace("_", "")
    sym = sym.replace("XBT", "BTC")
    if sym.endswith("USDT") or sym.endswith("USDC"):
        return sym
    if sym.endswith("USD"):
        return sym
    return ""


def _kraken_24h_snapshot(max_pairs: int) -> Dict[str, Any]:
    pairs_payload = _get("https://api.kraken.com/0/public/AssetPairs", timeout=20)
    if not pairs_payload.get("ok"):
        return {"ok": False, "error": f"assetpairs:{pairs_payload.get('error')}"}

    result = pairs_payload.get("data", {}).get("result", {})
    if not isinstance(result, dict):
        return {"ok": False, "error": "assetpairs_payload_invalid"}

    ws_pairs: List[str] = []
    symbol_map: Dict[str, str] = {}
    for pair_key, row in result.items():
        if not isinstance(row, dict):
            continue
        ws = str(row.get("wsname", "") or "").upper().strip()
        if not ws or "/" not in ws:
            continue
        quote = ws.split("/")[-1]
        if quote not in {"USD", "USDT", "USDC"}:
            continue
        req_pair = ws.replace("/", "")
        ws_pairs.append(req_pair)
        norm_symbol = _kraken_symbol_to_usd_pair(ws)
        if norm_symbol:
            symbol_map[str(pair_key).upper()] = norm_symbol
            altname = str(row.get("altname", "") or "").upper().strip()
            if altname:
                symbol_map[altname] = norm_symbol
            symbol_map[req_pair] = norm_symbol

    if not ws_pairs:
        return {"ok": False, "error": "no_kraken_usd_pairs"}

    # Kraken query strings can get too large with many pairs; fetch in chunks.
    requested_pairs = max(50, min(max_pairs, len(ws_pairs)))
    target_pairs = ws_pairs[:requested_pairs]
    batch_size = 120
    tickers: Dict[str, Any] = {}
    batch_errors: List[str] = []
    fetched_batches = 0

    for idx in range(0, len(target_pairs), batch_size):
        chunk = target_pairs[idx: idx + batch_size]
        if not chunk:
            continue
        pair_arg = ",".join(chunk)
        ticker_payload = _get("https://api.kraken.com/0/public/Ticker", params={"pair": pair_arg}, timeout=25)
        if not ticker_payload.get("ok"):
            batch_errors.append(str(ticker_payload.get("error") or "unknown_ticker_error"))
            continue

        chunk_rows = ticker_payload.get("data", {}).get("result", {})
        if not isinstance(chunk_rows, dict):
            batch_errors.append("ticker_payload_invalid")
            continue
        tickers.update(chunk_rows)
        fetched_batches += 1

    if not tickers:
        err = batch_errors[0] if batch_errors else "ticker_payload_invalid"
        return {"ok": False, "error": f"ticker:{err}"}

    rows: List[Dict[str, Any]] = []
    for ticker_key, row in tickers.items():
        if not isinstance(row, dict):
            continue
        symbol = symbol_map.get(str(ticker_key).upper(), "")
        if not symbol:
            wsname = str(row.get("wsname", "") or "")
            symbol = _kraken_symbol_to_usd_pair(wsname)
        if not symbol:
            continue
        close_px = _f((row.get("c") or [0.0])[0], 0.0)
        open_px = _f(row.get("o"), close_px)
        if close_px <= 0.0:
            continue
        pct = ((close_px / max(open_px, 1e-9)) - 1.0) * 100.0
        vol_base = _f((row.get("v") or [0.0, 0.0])[1], 0.0)
        vwap_24h = _f((row.get("p") or [0.0, close_px])[1], close_px)
        quote_volume = vol_base * max(vwap_24h, 0.0)
        high_px = _f((row.get("h") or [close_px, close_px])[1], close_px)
        low_px = _f((row.get("l") or [close_px, close_px])[1], close_px)
        count_24h = _f((row.get("t") or [0.0, 0.0])[1], 0.0)
        rows.append({
            "symbol": symbol,
            "lastPrice": close_px,
            "priceChangePercent": pct,
            "quoteVolume": quote_volume,
            "highPrice": high_px,
            "lowPrice": low_px,
            "count": count_24h,
            "venue": "kraken",
        })

    return {
        "ok": True,
        "rows": rows,
        "meta": {
            "pairs_requested": requested_pairs,
            "pairs_returned": len(tickers),
            "batches_fetched": fetched_batches,
            "batch_errors": batch_errors[:3],
        },
    }


def _build_unified_market_rows(max_scan: int) -> Dict[str, Any]:
    bus = _binanceus_24h_snapshot()
    krk = _kraken_24h_snapshot(max_scan)

    bus_rows = bus.get("rows", []) if isinstance(bus, dict) else []
    krk_rows = krk.get("rows", []) if isinstance(krk, dict) else []
    if not isinstance(bus_rows, list):
        bus_rows = []
    if not isinstance(krk_rows, list):
        krk_rows = []

    merged: Dict[str, Dict[str, Any]] = {}
    for row in bus_rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).upper().strip()
        if not symbol:
            continue
        cpy = dict(row)
        cpy.setdefault("venue", "binanceus")
        merged[symbol] = cpy
    for row in krk_rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).upper().strip()
        if not symbol:
            continue
        incoming_qv = _f(row.get("quoteVolume"), 0.0)
        current_qv = _f(merged.get(symbol, {}).get("quoteVolume"), 0.0)
        if symbol not in merged or incoming_qv > current_qv:
            merged[symbol] = dict(row)

    rows = list(merged.values())
    return {
        "ok": bool(rows),
        "rows": rows,
        "errors": {
            "binanceus": bus.get("error") if isinstance(bus, dict) else "unknown",
            "kraken": krk.get("error") if isinstance(krk, dict) else "unknown",
        },
        "venue_counts": {
            "binanceus": len(bus_rows),
            "kraken": len(krk_rows),
            "merged": len(rows),
        },
    }


def _update_symbol_history(history: Dict[str, List[float]], market_rows: List[Dict[str, Any]], keep: int = 20) -> None:
    for row in market_rows:
        sym = str(row.get("symbol", "")).upper().strip()
        if not sym:
            continue
        px = _f(row.get("lastPrice"), 0.0)
        if px <= 0.0:
            continue
        bucket = history.setdefault(sym, [])
        bucket.append(px)
        if len(bucket) > keep:
            del bucket[:-keep]


def _pct(prices: List[float], lookback: int) -> float:
    if len(prices) <= lookback or lookback <= 0:
        return 0.0
    p0 = _f(prices[-(lookback + 1)], 0.0)
    p1 = _f(prices[-1], 0.0)
    if p0 <= 0:
        return 0.0
    return (p1 / p0) - 1.0


def _recent_volatility(prices: List[float]) -> float:
    if not isinstance(prices, list) or len(prices) < 4:
        return 0.0
    returns: List[float] = []
    for idx in range(1, len(prices)):
        p0 = _f(prices[idx - 1], 0.0)
        p1 = _f(prices[idx], 0.0)
        if p0 > 0.0 and p1 > 0.0:
            returns.append(abs((p1 / p0) - 1.0))
    if not returns:
        return 0.0
    return sum(returns) / len(returns)


def _score_candidates(
    history: Dict[str, List[float]],
    market_rows: List[Dict[str, Any]],
    max_scan: int,
) -> Dict[str, Any]:
    ranked = []

    filtered = []
    for row in market_rows:
        sym = str(row.get("symbol", "")).upper().strip()
        if not (sym.endswith("USDT") or sym.endswith("USD") or sym.endswith("USDC")):
            continue
        quote_vol = _f(row.get("quoteVolume"), 0.0)
        last_px = _f(row.get("lastPrice"), 0.0)
        if quote_vol <= 0.0 or last_px <= 0.0:
            continue
        filtered.append((quote_vol, row))

    filtered.sort(key=lambda x: x[0], reverse=True)
    scan_rows = [row for _, row in filtered[: max(max_scan, 20)]]

    for row in scan_rows:
        sym = str(row.get("symbol", "")).upper().strip()
        prices = history.get(sym, [])
        pct24 = _f(row.get("priceChangePercent"), 0.0) / 100.0
        liq = _f(row.get("quoteVolume"), 0.0)

        if len(prices) < 6:
            # Warmup scoring: rely on 24h drift + liquidity until local tick history fills.
            r2 = pct24 * 0.25
            r4 = pct24 * 0.5
            r8 = pct24
            accel = 0.0
        else:
            r2 = _pct(prices, 2)
            r4 = _pct(prices, 4)
            r8 = _pct(prices, 8)
            accel = r2 - r4

        current_px = _f(row.get("lastPrice"), 0.0)
        high_px = _f(row.get("highPrice"), current_px)
        low_px = _f(row.get("lowPrice"), current_px)
        if current_px <= 0.0:
            continue
        if high_px <= 0.0:
            high_px = current_px
        if low_px <= 0.0:
            low_px = current_px
        if high_px < low_px:
            high_px, low_px = low_px, high_px
        trade_count = _f(row.get("count"), 0.0)
        range_size = max(high_px - low_px, 1e-12)
        near_high = min(max((current_px - low_px) / range_size, 0.0), 1.0)  # 0=at low, 1=at high
        # Trade density: trades-per-million-USD (high = lots of small accumulation orders)
        trade_density = min(trade_count / max(liq / 1_000_000.0, 0.001), 50_000.0) / 50_000.0
        # Breakout score: near-high position + acceleration + trade density; penalise chase
        chase_penalty = max(0.0, pct24 - 0.30) * 12.0
        breakout_score = (
            near_high * 6.0
            + max(accel, 0.0) * 5.0
            + max(r2, 0.0) * 4.0
            + max(pct24, 0.0) * 2.0
            + trade_density * 3.0
            - chase_penalty
            + min(liq / 1_000_000.0, 10.0) * 0.05
        )

        # Moonshot regime: prioritize fresh acceleration + positive drift + liquidity.
        moon_score = (
            max(r2, 0.0) * 5.0
            + max(r4, 0.0) * 3.0
            + max(r8, 0.0) * 2.0
            + max(accel, 0.0) * 4.0
            + max(pct24, 0.0) * 0.5
            + min(liq / 1_000_000.0, 8.0) * 0.05
        )

        # Fallback regime: rebound/continuation on liquid symbols when moon signals are thin.
        fallback_score = (
            max(-r4, 0.0) * 2.0
            + max(r2, 0.0) * 2.5
            + max(accel, 0.0) * 2.0
            + max(pct24, -0.10) * 0.2
            + min(liq / 1_000_000.0, 8.0) * 0.05
        )

        drawdown_24h = max(-pct24, 0.0)
        rebound_impulse = max(r2, 0.0) + max(accel, 0.0)
        dislocation_score = (
            drawdown_24h * 14.0
            + (1.0 - near_high) * 4.0
            + rebound_impulse * 18.0
            + trade_density * 2.5
            + min(liq / 1_000_000.0, 10.0) * 0.04
            - max(pct24, 0.0) * 1.5
        )
        dislocation_reason = _infer_dislocation_reason(pct24, near_high, r2, accel, trade_density)

        ranked.append(
            {
                "symbol": sym,
                "price": _f(row.get("lastPrice"), 0.0),
                "quote_volume": liq,
                "r2": r2,
                "r4": r4,
                "r8": r8,
                "accel": accel,
                "pct24": pct24,
                "near_high": near_high,
                "trade_density": trade_density,
                "range_pct_24h": (range_size / max(low_px, 1e-12)),
                "moon_score": moon_score,
                "fallback_score": fallback_score,
                "breakout_score": breakout_score,
                "drawdown_24h": drawdown_24h,
                "rebound_impulse": rebound_impulse,
                "dislocation_score": dislocation_score,
                "dislocation_reason": dislocation_reason,
            }
        )

    ranked_moon = sorted(ranked, key=lambda x: x["moon_score"], reverse=True)
    ranked_fallback = sorted(ranked, key=lambda x: x["fallback_score"], reverse=True)
    ranked_breakout = sorted(ranked, key=lambda x: x["breakout_score"], reverse=True)
    ranked_dislocation = sorted(ranked, key=lambda x: x["dislocation_score"], reverse=True)
    breadth_pos_pct24 = 0.0
    if ranked:
        breadth_pos_pct24 = len([x for x in ranked if _f(x.get("pct24"), 0.0) > 0.0]) / len(ranked)

    return {
        "scan_count": len(scan_rows),
        "scored_count": len(ranked),
        "breadth_pos_pct24": breadth_pos_pct24,
        "moon_ranked": ranked_moon,
        "fallback_ranked": ranked_fallback,
        "breakout_ranked": ranked_breakout,
        "dislocation_ranked": ranked_dislocation,
        "moon_top": ranked_moon[:20],
        "fallback_top": ranked_fallback[:20],
        "breakout_top": ranked_breakout[:20],
        "dislocation_top": ranked_dislocation[:20],
    }


def _calc_metrics(series: List[float]) -> Dict[str, Any]:
    import math as _math
    n = len(series)
    wins = len([x for x in series if x > 0])
    losses = len([x for x in series if x < 0])
    total = sum(series) if series else 0.0
    avg = (total / n) if n else 0.0
    gross_win = sum([x for x in series if x > 0])
    gross_loss = abs(sum([x for x in series if x < 0]))
    pf = gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    # Sharpe / Sortino (annualised; assumes each trade = 1 sample, ~288 trades/day crypto)
    ann_factor = _math.sqrt(288 * 365)
    if n >= 2:
        mean = avg
        variance = sum((x - mean) ** 2 for x in series) / (n - 1)
        std = _math.sqrt(variance) if variance > 0 else 1e-9
        downside_sq = sum(x ** 2 for x in series if x < 0)
        downside_dev = _math.sqrt(downside_sq / n) if downside_sq > 0 else 1e-9
        sharpe = (mean / std) * ann_factor
        sortino = (mean / downside_dev) * ann_factor
    else:
        sharpe = sortino = 0.0
    # Max drawdown on cumulative PnL curve (bounded to 0..100%).
    peak = cum = max_dd = 0.0
    for x in series:
        cum += x
        if cum > peak:
            peak = cum
        dd = (peak - cum) / max(abs(peak), abs(cum), 1.0)
        dd = min(max(dd, 0.0), 1.0)
        if dd > max_dd:
            max_dd = dd
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round((wins / n) if n else 0.0, 4),
        "total_pnl_usd": round(total, 4),
        "avg_pnl_usd": round(avg, 4),
        "profit_factor": round(pf, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_drawdown_pct": round(max_dd * 100.0, 4),
    }


def _write_investor_scorecard(scoreboard: Dict[str, Any], equity_usd: float, seed_usd: float, abs_cycle: int, profile: str) -> None:
    """Write investor_proof_scorecard.json + append one row to the .jsonl history per cycle."""
    totals = scoreboard.get("totals", {}) if isinstance(scoreboard, dict) else {}
    pnl_hist = scoreboard.get("pnl_history_usd", []) if isinstance(scoreboard, dict) else []
    if not scoreboard.get("first_trade_utc") and pnl_hist:
        scoreboard["first_trade_utc"] = now_utc()
    first_trade_utc = scoreboard.get("first_trade_utc", now_utc())
    try:
        from datetime import datetime, timezone as _tz
        t0 = datetime.fromisoformat(first_trade_utc)
        elapsed_days = max((datetime.now(_tz.utc) - t0).total_seconds() / 86400.0, 1.0 / 1440.0)
    except Exception:
        elapsed_days = 1.0
    years = elapsed_days / 365.0
    net_pnl_usd = _f(totals.get("total_pnl_usd"), 0.0)
    final_equity = seed_usd + net_pnl_usd
    cagr = (((final_equity / max(seed_usd, 1.0)) ** (1.0 / max(years, 1e-6))) - 1.0) * 100.0 if final_equity > 0 else 0.0
    mdd = _f(totals.get("max_drawdown_pct"), 0.0)
    annualised_return_pct = (net_pnl_usd / max(seed_usd, 1.0)) * (365.0 / max(elapsed_days, 1.0)) * 100.0
    calmar = annualised_return_pct / max(abs(mdd), 0.01)
    scorecard = {
        "schema": "luma_investor_proof_v1",
        "generated_utc": now_utc(),
        "profile": profile,
        "absolute_cycle": abs_cycle,
        "seed_capital_usd": round(seed_usd, 2),
        "current_equity_usd": round(equity_usd, 2),
        "net_pnl_usd": round(net_pnl_usd, 2),
        "net_pnl_pct": round((net_pnl_usd / max(seed_usd, 1.0)) * 100.0, 4),
        "elapsed_days": round(elapsed_days, 4),
        "closed_trades": _i(totals.get("n"), 0),
        "wins": _i(totals.get("wins"), 0),
        "losses": _i(totals.get("losses"), 0),
        "win_rate_pct": round(_f(totals.get("win_rate"), 0.0) * 100.0, 2),
        "profit_factor": round(_f(totals.get("profit_factor"), 0.0), 4),
        "sharpe_rolling": round(_f(totals.get("sharpe"), 0.0), 4),
        "sortino_rolling": round(_f(totals.get("sortino"), 0.0), 4),
        "max_drawdown_pct": round(mdd, 4),
        "cagr_pct": round(cagr, 4),
        "calmar_ratio": round(calmar, 4),
        "annualised_return_pct": round(annualised_return_pct, 4),
        "ledger_file": str(BINANCEUS_PAPER_LEDGER_FILE),
        "ledger_sha256": sha256_file(BINANCEUS_PAPER_LEDGER_FILE),
    }
    raw = json.dumps(scorecard, separators=(",", ":"), sort_keys=True)
    scorecard["scorecard_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    save_json(INVESTOR_SCORECARD_FILE, scorecard)
    append_jsonl(INVESTOR_SCORECARD_HISTORY_FILE, scorecard)


def _update_scoreboard(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    board = load_json(
        BINANCEUS_PAPER_SCOREBOARD_FILE,
        {
            "updated_utc": now_utc(),
            "pnl_history_usd": [],
            "regime_pnl_history_usd": {"moonshot": [], "fallback": []},
            "totals": {},
            "regimes": {},
        },
    )

    pnl_hist = board.get("pnl_history_usd", [])
    if not isinstance(pnl_hist, list):
        pnl_hist = []

    reg_hist = board.get("regime_pnl_history_usd", {})
    if not isinstance(reg_hist, dict):
        reg_hist = {}
    reg_hist.setdefault("moonshot", [])
    reg_hist.setdefault("fallback", [])

    for ev in events:
        if ev.get("event_type") != "binanceus_paper_fill" or ev.get("side") != "sell":
            continue
        pnl = _f(ev.get("pnl_usd"), 0.0)
        pnl_hist.append(pnl)
        regime = str(ev.get("regime", "fallback"))
        if regime not in reg_hist:
            reg_hist[regime] = []
        reg_hist[regime].append(pnl)

    keep = 400
    if len(pnl_hist) > keep:
        pnl_hist = pnl_hist[-keep:]
    for k in list(reg_hist.keys()):
        arr = reg_hist.get(k, [])
        if isinstance(arr, list) and len(arr) > keep:
            reg_hist[k] = arr[-keep:]

    totals = _calc_metrics(pnl_hist)
    regimes = {k: _calc_metrics(v if isinstance(v, list) else []) for k, v in reg_hist.items()}

    board.update(
        {
            "updated_utc": now_utc(),
            "pnl_history_usd": pnl_hist,
            "regime_pnl_history_usd": reg_hist,
            "totals": totals,
            "regimes": regimes,
        }
    )
    save_json(BINANCEUS_PAPER_SCOREBOARD_FILE, board)
    return board


def _default_binanceus_paper_state(profile_key: str, preset: Dict[str, Any], seed_capital: float, price: float | None) -> Dict[str, Any]:
    seeded_cash = round(max(seed_capital, 1000.0), 6)
    return {
        "started_utc": now_utc(),
        "cash_usd": seeded_cash,
        "initial_cash_usd": seeded_cash,
        "seed_capital_usd": seeded_cash,
        "realized_pnl_usd": 0.0,
        "trade_count": 0,
        "wins": 0,
        "losses": 0,
        "last_action": "INIT",
        "last_price": price,
        "equity_usd": seeded_cash,
        "positions": {},
        "recent_exits": {},
        "history": {},
        "last_regime": "moonshot",
        "last_candidates": [],
        "scan_count": 0,
        "scored_count": 0,
        "max_positions": int(preset.get("max_positions", 6)),
        "max_scan_symbols": int(preset.get("max_scan_symbols", 300)),
        "base_risk_fraction": float(preset.get("base_risk_fraction", 0.07)),
        "profile": profile_key,
    }


def build_institutional_crypto_paper_report(payload: Dict[str, Any], seed_capital: float, reset_state: bool) -> Dict[str, Any]:
    engine = payload.get("binanceus_paper_engine", {}) if isinstance(payload, dict) else {}
    alpaca_true = payload.get("alpaca_true_paper_engine", {}) if isinstance(payload, dict) else {}
    state = engine.get("state", {}) if isinstance(engine, dict) else {}
    alpaca_state = alpaca_true.get("state", {}) if isinstance(alpaca_true, dict) else {}
    scoreboard_totals = engine.get("scoreboard_totals", {}) if isinstance(engine, dict) else {}
    quality_gate = engine.get("quality_gate", {}) if isinstance(engine, dict) else {}
    event = engine.get("event", {}) if isinstance(engine, dict) else {}
    hybrid_top = engine.get("hybrid_top", []) if isinstance(engine, dict) else []
    fallback_top = engine.get("fallback_top", []) if isinstance(engine, dict) else []
    moon_top = engine.get("moon_top", []) if isinstance(engine, dict) else []
    dislocation_top = engine.get("dislocation_top", []) if isinstance(engine, dict) else []
    positions = state.get("positions", {}) if isinstance(state, dict) else {}
    scientific_allocator = state.get("scientific_allocator", {}) if isinstance(state, dict) else {}
    regime_controller = state.get("regime_controller", {}) if isinstance(state, dict) else {}

    use_alpaca_truth = bool(alpaca_true.get("ok")) and bool(alpaca_state)

    if use_alpaca_truth:
        initial_equity = _f(alpaca_state.get("initial_cash_usd"), max(seed_capital, 1000.0))
        if initial_equity <= 0.0:
            initial_equity = max(seed_capital, 1000.0)
        equity = _f(alpaca_state.get("equity_usd"), initial_equity)
        cash = _f(alpaca_state.get("cash_usd"), initial_equity)
        realized = _f(alpaca_state.get("realized_pnl_usd"), 0.0)
        gross = max(equity - cash, 0.0)
        unrealized = max((equity - cash) - realized, 0.0)
        positions_open = len(alpaca_state.get("open_positions", {})) if isinstance(alpaca_state.get("open_positions", {}), dict) else 0
    else:
        initial_equity = _f(state.get("initial_cash_usd"), max(seed_capital, 1000.0))
        equity = _f(state.get("equity_usd"), initial_equity)
        cash = _f(state.get("cash_usd"), initial_equity)
        realized = _f(state.get("realized_pnl_usd"), 0.0)
        unrealized = _f(state.get("unrealized_pnl_usd"), 0.0)
        gross = _f(state.get("gross_position_value_usd"), 0.0)
        positions_open = len(positions)
    equity_return = ((equity / initial_equity) - 1.0) if initial_equity > 0 else 0.0

    report = {
        "generated_utc": now_utc(),
        "mode": "alpaca_true_paper_execution" if use_alpaca_truth else "seeded_institutional_crypto_paper",
        "truth_mode": "real_alpaca_paper_fills" if use_alpaca_truth else "simulated_multi_exchange_paper",
        "profile": payload.get("profile"),
        "seed_request": {
            "requested_seed_capital_usd": round(max(seed_capital, 1000.0), 6),
            "reset_state": bool(reset_state),
            "active_initial_cash_usd": round(initial_equity, 6),
        },
        "portfolio": {
            "cash_usd": round(cash, 6),
            "gross_position_value_usd": round(gross, 6),
            "equity_usd": round(equity, 6),
            "realized_pnl_usd": round(realized, 6),
            "unrealized_pnl_usd": round(unrealized, 6),
            "return_pct": round(equity_return, 6),
            "positions_open": positions_open,
        },
        "decision_audit": {
            "cycle": payload.get("cycle"),
            "regime": engine.get("regime"),
            "hybrid_weight": engine.get("hybrid_weight"),
            "breadth_pos_pct24": engine.get("breadth_pos_pct24"),
            "scan_count": engine.get("scan_count"),
            "scored_count": engine.get("scored_count"),
            "last_action": event.get("action"),
            "last_event": event,
            "scientific_allocator": scientific_allocator,
            "regime_controller": regime_controller,
            "quality_gate": quality_gate,
            "top_candidates": {
                "hybrid": hybrid_top[:5],
                "moon": moon_top[:5],
                "fallback": fallback_top[:5],
                "dislocation": dislocation_top[:5],
            },
        },
        "scoreboard": scoreboard_totals,
        "runtime_guard": payload.get("runtime_guard"),
        "artifacts": {
            "status_file": str(STATUS_FILE),
            "ledger_file": str(BINANCEUS_PAPER_LEDGER_FILE),
            "state_file": str(BINANCEUS_PAPER_STATE_FILE),
            "scoreboard_file": str(BINANCEUS_PAPER_SCOREBOARD_FILE),
            "report_file": str(INSTITUTIONAL_PAPER_REPORT_FILE),
            "alpaca_true_state_file": str(ALPACA_TRUE_PAPER_STATE_FILE),
            "alpaca_true_ledger_file": str(ALPACA_TRUE_PAPER_LEDGER_FILE),
        },
    }
    save_json(INSTITUTIONAL_PAPER_REPORT_FILE, report)

    hashes = {
        "generated_utc": now_utc(),
        "files": [
            {"path": str(STATUS_FILE), "sha256": sha256_file(STATUS_FILE)},
            {"path": str(BINANCEUS_PAPER_LEDGER_FILE), "sha256": sha256_file(BINANCEUS_PAPER_LEDGER_FILE)},
            {"path": str(BINANCEUS_PAPER_STATE_FILE), "sha256": sha256_file(BINANCEUS_PAPER_STATE_FILE)},
            {"path": str(BINANCEUS_PAPER_SCOREBOARD_FILE), "sha256": sha256_file(BINANCEUS_PAPER_SCOREBOARD_FILE)},
            {"path": str(ALPACA_TRUE_PAPER_STATE_FILE), "sha256": sha256_file(ALPACA_TRUE_PAPER_STATE_FILE)},
            {"path": str(ALPACA_TRUE_PAPER_LEDGER_FILE), "sha256": sha256_file(ALPACA_TRUE_PAPER_LEDGER_FILE)},
            {"path": str(INSTITUTIONAL_PAPER_REPORT_FILE), "sha256": sha256_file(INSTITUTIONAL_PAPER_REPORT_FILE)},
        ],
    }
    save_json(INSTITUTIONAL_PAPER_HASH_FILE, hashes)
    report["artifact_hash_file"] = str(INSTITUTIONAL_PAPER_HASH_FILE)
    report["artifact_hashes"] = hashes["files"]
    save_json(INSTITUTIONAL_PAPER_REPORT_FILE, report)
    return report


def run_binanceus_paper_logic(price: float | None, cycle: int, profile: str, seed_capital: float, reset_state: bool = False) -> Dict[str, Any]:
    profile_key = profile if profile in PROFILE_PRESETS else DEFAULT_PROFILE
    preset = PROFILE_PRESETS.get(profile_key, PROFILE_PRESETS[DEFAULT_PROFILE])
    default_state = _default_binanceus_paper_state(profile_key, preset, seed_capital, price)
    order_router = OrderRouter()
    shadow_runner = ShadowRunner()
    trade_ledger = TradeLedger(str(TRADE_LEDGER_CSV_FILE), str(TRADE_LEDGER_JSONL_FILE))
    audit_chain = AuditChain(EXECUTION_AUDIT_CHAIN_FILE)

    state = default_state if reset_state else load_json(BINANCEUS_PAPER_STATE_FILE, default_state)

    cash = _f(state.get("cash_usd"), _f(default_state.get("cash_usd"), 10000.0))
    realized = _f(state.get("realized_pnl_usd"), 0.0)
    trades = _i(state.get("trade_count"), 0)
    wins = _i(state.get("wins"), 0)
    losses = _i(state.get("losses"), 0)
    max_positions = max(_i(state.get("max_positions"), _i(preset.get("max_positions"), 6)), 1)
    max_scan = max(_i(state.get("max_scan_symbols"), _i(preset.get("max_scan_symbols"), 300)), 25)
    base_risk = min(max(_f(state.get("base_risk_fraction"), _f(preset.get("base_risk_fraction"), 0.07)), 0.01), 0.30)
    external_intel = _load_external_intel()
    base_risk = min(max(base_risk * _f(external_intel.get("risk_multiplier"), 1.0), 0.01), 0.40)
    max_scan = max(int(max_scan * _f(external_intel.get("scan_multiplier"), 1.0)), 25)

    # Profile-local boost allows aggressive paper discovery even when historical KPI penalties are stale.
    base_risk = min(max(base_risk * _f(preset.get("aggression_boost"), 1.0), 0.01), 0.45)
    max_scan = max(int(max_scan * _f(preset.get("scan_boost"), 1.0)), 25)

    positions = state.get("positions", {})
    if not isinstance(positions, dict):
        positions = {}
    recent_exits = state.get("recent_exits", {})
    if not isinstance(recent_exits, dict):
        recent_exits = {}
    history = state.get("history", {})
    if not isinstance(history, dict):
        history = {}
    abs_cycle = _i(state.get("absolute_cycle"), 0) + 1

    # Legacy migration from previous single-symbol schema.
    legacy_qty = _f(state.get("btc_qty"), 0.0)
    if legacy_qty > 0.0 and (not positions) and price is not None and price > 0:
        cash += legacy_qty * float(price)
    for old_key in ["btc_qty", "avg_entry"]:
        if old_key in state:
            state.pop(old_key, None)

    snap = _build_unified_market_rows(max_scan)
    if not snap.get("ok"):
        event = {
            "timestamp_utc": now_utc(),
            "cycle": cycle,
            "absolute_cycle": abs_cycle,
            "event_type": "binanceus_paper_mark",
            "action": "HOLD",
            "error": snap.get("errors") or snap.get("error"),
        }
        append_jsonl(BINANCEUS_PAPER_LEDGER_FILE, event)
        state.update(
            {
                "last_tick_utc": now_utc(),
                "last_action": "HOLD",
                "last_error": snap.get("errors") or snap.get("error"),
                "positions": positions,
                "history": history,
            }
        )
        save_json(BINANCEUS_PAPER_STATE_FILE, state)
        return {
            "ok": False,
            "state_file": str(BINANCEUS_PAPER_STATE_FILE),
            "ledger_file": str(BINANCEUS_PAPER_LEDGER_FILE),
            "event": event,
            "state": state,
        }

    rows = snap.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    venue_counts = snap.get("venue_counts", {}) if isinstance(snap, dict) else {}
    snap_errors = snap.get("errors", {}) if isinstance(snap, dict) else {}

    _update_symbol_history(history, rows, keep=20)
    scored = _score_candidates(history, rows, max_scan=max_scan)

    moon_ranked = scored.get("moon_ranked", []) if isinstance(scored, dict) else []
    fallback_ranked = scored.get("fallback_ranked", []) if isinstance(scored, dict) else []
    breakout_ranked = scored.get("breakout_ranked", []) if isinstance(scored, dict) else []
    dislocation_ranked = scored.get("dislocation_ranked", []) if isinstance(scored, dict) else []
    moon_top = scored.get("moon_top", []) if isinstance(scored, dict) else []
    fallback_top = scored.get("fallback_top", []) if isinstance(scored, dict) else []
    dislocation_top = scored.get("dislocation_top", []) if isinstance(scored, dict) else []
    breadth = _f(scored.get("breadth_pos_pct24"), 0.5)
    moon_trigger = _f(preset.get("moon_trigger"), 0.014)
    moon_ready = bool(moon_top) and _f(moon_top[0].get("moon_score"), 0.0) >= moon_trigger

    score_regime_override = str(preset.get("score_regime", "")).lower()
    preferred_regime = str(external_intel.get("preferred_regime", "")).lower()
    if not score_regime_override and preferred_regime in {"breakout", "moonshot", "fallback"}:
        score_regime_override = preferred_regime

    base_w = _f(preset.get("hybrid_weight_base"), 0.58)
    breadth_k = _f(preset.get("hybrid_weight_breadth_k"), 0.30)
    hybrid_weight = min(max(base_w + (breadth - 0.5) * breadth_k, 0.20), 0.85)

    if score_regime_override == "breakout":
        hybrid_ranked = breakout_ranked
        regime = "breakout"
    elif score_regime_override == "dislocation":
        hybrid_ranked = dislocation_ranked
        regime = "dislocation"
    else:
        combined: Dict[str, Dict[str, Any]] = {}
        for row in moon_ranked:
            combined[row["symbol"]] = dict(row)
        for row in fallback_ranked:
            if row["symbol"] not in combined:
                combined[row["symbol"]] = dict(row)
        for row in dislocation_ranked:
            if row["symbol"] not in combined:
                combined[row["symbol"]] = dict(row)

        dislocation_weight = min(max(_f(preset.get("dislocation_weight"), 0.20), 0.0), 0.70)
        moon_component = max(1.0 - dislocation_weight, 0.0)

        for sym, row in combined.items():
            row["symbol"] = sym
            moon_fallback_score = (hybrid_weight * _f(row.get("moon_score"), 0.0)) + ((1.0 - hybrid_weight) * _f(row.get("fallback_score"), 0.0))
            row["hybrid_score"] = (moon_component * moon_fallback_score) + (dislocation_weight * _f(row.get("dislocation_score"), 0.0))

        hybrid_ranked = sorted(list(combined.values()), key=lambda x: x.get("hybrid_score", 0.0), reverse=True)
        regime = "moonshot" if moon_ready else "fallback"

    pick_engine_map: Dict[str, str] = {}
    if str(preset.get("engine_mode", "")).lower() == "triplet":
        slots_breakout = max(_i(preset.get("triplet_slots_breakout"), max_positions // 3), 1)
        slots_moon = max(_i(preset.get("triplet_slots_moon"), max_positions // 3), 1)
        slots_fallback = max(_i(preset.get("triplet_slots_fallback"), max_positions // 3), 1)
        picks = []
        used: Set[str] = set()

        def _take(rows: List[Dict[str, Any]], slots: int, engine_name: str) -> None:
            nonlocal picks
            count = 0
            for row in rows:
                sym = str(row.get("symbol", "")).upper().strip()
                if not sym or sym in used:
                    continue
                used.add(sym)
                pick_engine_map[sym] = engine_name
                picks.append(row)
                count += 1
                if count >= slots or len(picks) >= max_positions:
                    break

        _take(breakout_ranked, slots_breakout, "breakout")
        if len(picks) < max_positions:
            _take(moon_ranked, slots_moon, "moonshot")
        if len(picks) < max_positions:
            _take(fallback_ranked, slots_fallback, "fallback")
        if len(picks) < max_positions:
            _take(hybrid_ranked, max_positions - len(picks), regime)
    else:
        picks = hybrid_ranked[: max_positions]
        for row in picks:
            sym = str(row.get("symbol", "")).upper().strip()
            if sym:
                pick_engine_map[sym] = regime

    market_price_map: Dict[str, float] = {}
    for row in rows:
        sym = str(row.get("symbol", "")).upper().strip()
        px = _f(row.get("lastPrice"), 0.0)
        if sym and px > 0.0:
            market_price_map[sym] = px

    events: List[Dict[str, Any]] = []

    # Exit logic for open positions.
    for sym in list(positions.keys()):
        pos = positions.get(sym, {})
        qty = _f(pos.get("qty"), 0.0)
        entry = _f(pos.get("entry"), 0.0)
        if qty <= 0.0 or entry <= 0.0:
            positions.pop(sym, None)
            continue
        mark = market_price_map.get(sym)
        if not mark:
            continue

        hold_cycles = max(cycle - _i(pos.get("opened_cycle"), cycle), 0)
        hold_cycles = max(abs_cycle - _i(pos.get("opened_cycle"), abs_cycle), 0)
        pnl_pct = (mark / entry) - 1.0
        pos_engine = str(pos.get("engine", regime)).lower()
        if pos_engine == "fallback":
            tp = _f(preset.get("tp_fallback"), 0.010)
        elif pos_engine == "breakout":
            tp = _f(preset.get("tp_breakout"), _f(preset.get("tp_moon"), 0.018))
        elif pos_engine == "dislocation":
            tp = _f(preset.get("tp_dislocation"), max(_f(preset.get("tp_moon"), 0.018), 0.035))
        else:
            tp = _f(preset.get("tp_moon"), 0.018)
        sl = _f(preset.get("sl"), -0.007)
        timeout = _i(preset.get("timeout_cycles"), 12)
        should_exit = pnl_pct >= tp or pnl_pct <= sl or hold_cycles >= timeout
        if not should_exit:
            continue

        friction = _execution_friction_rates(preset)
        sell_slip = max(1.0 - _f(friction.get("slippage_rate"), 0.0), 0.0)
        effective_mark = mark * sell_slip
        gross_proceeds = qty * effective_mark
        sell_route = "maker" if pnl_pct >= tp and hold_cycles < timeout else "taker"
        sell_urgency = _resolve_urgency(abs(pnl_pct), _f(pos.get("trade_density", 0.0), 0.0), 0.0, sell_route)
        sell_fee_rate = _f(friction.get("maker_fee_rate" if sell_route == "maker" else "taker_fee_rate"), 0.0)
        sell_fee = gross_proceeds * sell_fee_rate
        proceeds = max(gross_proceeds - sell_fee, 0.0)
        cost_basis = _f(pos.get("cost_basis_usd"), qty * entry)
        pnl = proceeds - cost_basis
        cash += proceeds
        realized += pnl
        trades += 1
        if pnl >= 0:
            wins += 1
        else:
            losses += 1

        ev = {
            "timestamp_utc": now_utc(),
            "cycle": cycle,
            "absolute_cycle": abs_cycle,
            "event_type": "binanceus_paper_fill",
            "side": "sell",
            "symbol": sym,
            "qty": round(qty, 10),
            "fill_price": round(effective_mark, 6),
            "mark_price": round(mark, 6),
            "notional_usd": round(proceeds, 4),
            "entry_price": round(entry, 6),
            "cost_basis_usd": round(cost_basis, 6),
            "sell_fee_usd": round(sell_fee, 6),
            "execution_route": sell_route,
            "slippage_bps": round(_f(friction.get("slippage_bps"), 0.0), 4),
            "maker_fee_bps": round(_f(friction.get("maker_fee_bps"), 0.0), 4),
            "taker_fee_bps": round(_f(friction.get("taker_fee_bps"), 0.0), 4),
            "pnl_usd": round(pnl, 6),
            "pnl_pct": round(pnl_pct, 6),
            "action": "SELL",
            "reason": "tp_sl_timeout",
            "regime": pos_engine,
        }
        bid = mark * max(1.0 - (_f(friction.get("slippage_rate"), 0.0) * 0.5), 0.0)
        ev["trade_id"] = f"LUMA-PAPER-SELL-{abs_cycle}-{sym}"
        ask = mark * (1.0 + (_f(friction.get("slippage_rate"), 0.0) * 0.5))
        shadow_px, shadow_slip_bps = shadow_runner.simulate_fill(bid, ask, "sell", sell_urgency)
        shadow_runner.append_ledger(
            str(SHADOW_LEDGER_CSV_FILE),
            ShadowFill(
                ts_utc=str(ev.get("timestamp_utc")),
                symbol=sym,
                side="sell",
                qty=round(qty, 10),
                est_fill=round(shadow_px, 6),
                slip_bps=round(shadow_slip_bps, 6),
            ),
        )
        route_intent = RouteIntent(
            symbol=sym,
            side="sell",
            qty=qty,
            urgency=sell_urgency,
            entry_price=effective_mark,
            stop_price=None,
            take_profit=None,
            reduce_only=True,
        )
        order_template = order_router.build_primary(route_intent, validate_only=True)
        close_template = order_router.build_close_template(route_intent)
        ev["shadow_fill"] = {"est_fill": round(shadow_px, 6), "slip_bps": round(shadow_slip_bps, 6)}
        ev["order_template"] = order_template
        if close_template is not None:
            ev["close_template"] = close_template
        ledger_hash = trade_ledger.append(
            {
                "timestamp": str(ev.get("timestamp_utc")),
                "symbol": sym,
                "side": "sell",
                "status": "CLOSED",
                "execution_mode": sell_route,
                "close_reason": "tp_sl_timeout",
                "entry_price": round(entry, 6),
                "exit_price": round(effective_mark, 6),
                "qty": round(qty, 10),
                "size_usd": round(cost_basis, 6),
                "pnl": round(pnl, 6),
                "pnl_pct": round(pnl_pct * 100.0, 6),
                "net_pnl": round(pnl, 6),
                "net_pnl_pct": round(pnl_pct * 100.0, 6),
                "round_trip_fee_usd": round(_f(pos.get("entry_fee_paid_usd"), 0.0) + sell_fee, 6),
            }
        )
        audit_event = audit_chain.append("paper_sell", {"symbol": sym, "route": sell_route, "pnl_usd": round(pnl, 6), "ledger_hash": ledger_hash})
        ev["ledger_hash"] = ledger_hash
        ev["trade_id"] = ledger_hash
        ev["audit_hash"] = audit_event.get("event_hash")
        events.append(ev)
        recent_exits[sym] = abs_cycle
        positions.pop(sym, None)

    # Entry logic for top picks.
    held = set(positions.keys())
    slots_left = max(max_positions - len(held), 0)
    gate_min_edge = _f(preset.get("min_edge"), 0.0)
    gate_min_pct24 = _f(preset.get("min_pct24"), -999.0)
    gate_max_pct24 = _f(preset.get("max_pct24"), 9999.0)
    gate_min_qv = _f(preset.get("min_quote_volume_usd"), 0.0)
    gate_min_near_high = _f(preset.get("min_near_high"), 0.0)
    gate_min_r2 = _f(preset.get("min_r2"), -999.0)
    gate_min_dislocation = _f(preset.get("min_dislocation_score"), -999.0)
    gate_bad_tick_drawdown = _f(preset.get("bad_tick_drawdown_threshold"), 0.70)
    gate_bad_tick_trade_density = _f(preset.get("bad_tick_trade_density_threshold"), 0.15)
    gate_bad_tick_range = _f(preset.get("bad_tick_range_threshold"), 5.0)
    gate_reentry_cooldown = _i(preset.get("reentry_cooldown_cycles"), 0)
    allocator_mode = str(preset.get("allocator_mode", "scientific_hybrid"))
    max_single_position_pct = min(max(_f(preset.get("max_single_position_pct"), 0.22), 0.05), 0.50)
    max_gross_heat_pct = min(max(_f(preset.get("max_gross_heat_pct"), 0.70), max_single_position_pct), 0.95)
    target_position_vol_pct = min(max(_f(preset.get("target_position_vol_pct"), 0.035), 0.005), 0.25)
    uncertainty_penalty_k = min(max(_f(preset.get("uncertainty_penalty_k"), 1.20), 0.0), 5.0)
    min_diversified_slots = max(_i(preset.get("min_diversified_slots"), 4), 1)
    vol_scalar_floor = min(max(_f(preset.get("vol_scalar_floor"), 0.45), 0.10), 1.0)
    vol_scalar_ceiling = max(_f(preset.get("vol_scalar_ceiling"), 1.20), 1.0)
    gate_rejects = {
        "low_edge": 0,
        "low_pct24": 0,
        "low_quote_volume": 0,
        "low_near_high": 0,
        "low_r2": 0,
        "low_dislocation": 0,
        "suspicious_bad_tick": 0,
        "drawdown_halt": 0,
        "cooldown_reentry": 0,
        "skip_invalid_or_held": 0,
        "skip_bad_price": 0,
        "skip_notional_too_small": 0,
        "single_position_cap": 0,
        "gross_heat_cap": 0,
        "triplet_sleeve_cap": 0,
    }

    current_gross_position_value = 0.0
    for held_sym, held_pos in positions.items():
        held_qty = _f(held_pos.get("qty"), 0.0)
        held_entry = _f(held_pos.get("entry"), 0.0)
        held_mark = market_price_map.get(held_sym, held_entry)
        current_gross_position_value += held_qty * held_mark

    triplet_mode = str(preset.get("engine_mode", "")).lower() == "triplet"
    sleeve_caps_pct = {
        "breakout": min(max(_f(preset.get("triplet_breakout_cap_pct"), 0.45), 0.05), 0.80),
        "moonshot": min(max(_f(preset.get("triplet_moon_cap_pct"), 0.35), 0.05), 0.80),
        "fallback": min(max(_f(preset.get("triplet_fallback_cap_pct"), 0.20), 0.05), 0.80),
    }
    sleeve_notional_by_engine = {"breakout": 0.0, "moonshot": 0.0, "fallback": 0.0}
    for held_sym, held_pos in positions.items():
        eng = str(held_pos.get("engine", regime)).lower()
        qty = _f(held_pos.get("qty"), 0.0)
        entry = _f(held_pos.get("entry"), 0.0)
        mark = market_price_map.get(held_sym, entry)
        if eng in sleeve_notional_by_engine:
            sleeve_notional_by_engine[eng] += qty * mark

    equity_basis = max(cash + current_gross_position_value, 1.0)
    edge_key = "breakout_score" if regime == "breakout" else ("moon_score" if regime == "moonshot" else ("dislocation_score" if regime == "dislocation" else "fallback_score"))
    top_edge = max(_f(picks[0].get(edge_key), 0.0), 1e-9) if picks else 1e-9
    available_heat_pct = max(((equity_basis * max_gross_heat_pct) - current_gross_position_value) / equity_basis, 0.0)
    turnover_reference = state.get("scientific_allocator", {}).get("last_target_weights", {}) if isinstance(state.get("scientific_allocator", {}), dict) else {}
    optimizer_risk_aversion = min(max(_f(preset.get("optimizer_risk_aversion"), 6.0), 0.10), 100.0)
    optimizer_turnover_penalty = min(max(_f(preset.get("optimizer_turnover_penalty"), 0.40), 0.0), 10.0)
    prior_regime_state = state.get("regime_controller", {}) if isinstance(state.get("regime_controller", {}), dict) else {}
    regime_controller = infer_market_regime(history, hybrid_ranked[:20], breadth, prior_state=prior_regime_state)
    preferred_family = str(regime_controller.get("preferred_family", "balanced")).lower()
    family_confidence = _f(regime_controller.get("family_confidence"), 0.5)
    regime_heat_multiplier = min(max(_f(regime_controller.get("heat_multiplier"), 1.0), 0.30), 1.20)
    regime_risk_aversion_multiplier = min(max(_f(regime_controller.get("risk_aversion_multiplier"), 1.0), 0.50), 2.50)
    regime_confidence_multiplier = min(max(_f(regime_controller.get("confidence_multiplier"), 1.0), 0.50), 1.50)
    max_single_position_pct = min(max(max_single_position_pct * regime_heat_multiplier, 0.04), 0.50)
    max_gross_heat_pct = min(max(max_gross_heat_pct * regime_heat_multiplier, max_single_position_pct), 0.95)
    venue_health_multiplier = 1.0
    if isinstance(snap_errors, dict) and isinstance(venue_counts, dict):
        if snap_errors.get("binanceus") and _i(venue_counts.get("binanceus"), 0) <= 0:
            venue_health_multiplier *= 0.85
        if snap_errors.get("kraken") and _i(venue_counts.get("kraken"), 0) <= 0:
            venue_health_multiplier *= 0.85
    max_gross_heat_pct = min(max(max_gross_heat_pct * venue_health_multiplier, max_single_position_pct), 0.95)
    available_heat_pct = max(((equity_basis * max_gross_heat_pct) - current_gross_position_value) / equity_basis, 0.0)
    optimizer_risk_aversion *= regime_risk_aversion_multiplier
    peak_equity = max(_f(state.get("peak_equity_usd"), equity_basis), equity_basis)
    drawdown_halt_pct = min(max(_f(preset.get("max_drawdown_halt_pct"), 0.35), 0.05), 0.90)
    current_drawdown_pct = max(0.0, 1.0 - (equity_basis / max(peak_equity, 1e-9)))
    if current_drawdown_pct >= drawdown_halt_pct:
        slots_left = 0
        gate_rejects["drawdown_halt"] += 1
    candidate_entries: List[Dict[str, Any]] = []

    for pick_idx, pick in enumerate(picks):
        if slots_left <= 0:
            break
        sym = str(pick.get("symbol", "")).upper().strip()
        if not sym or sym in held:
            gate_rejects["skip_invalid_or_held"] += 1
            continue
        px = _f(pick.get("price"), 0.0)
        if px <= 0.0:
            gate_rejects["skip_bad_price"] += 1
            continue

        pick_engine = str(pick_engine_map.get(sym, regime)).lower()
        if pick_engine == "breakout":
            edge = _f(pick.get("breakout_score"), 0.0)
        elif pick_engine == "fallback":
            edge = _f(pick.get("fallback_score"), 0.0)
        elif pick_engine == "dislocation":
            # Normalize dislocation_score (0–15 range) into 0–1 edge space so it
            # can be compared against gate_min_edge thresholds cleanly.
            edge = min(_f(pick.get("dislocation_score"), 0.0) / 10.0, 1.0)
        else:
            edge = _f(pick.get("moon_score"), 0.0)
        pct24 = _f(pick.get("pct24"), 0.0)
        r2 = _f(pick.get("r2"), 0.0)
        r4 = _f(pick.get("r4"), 0.0)
        r8 = _f(pick.get("r8"), 0.0)
        qv = _f(pick.get("quote_volume"), 0.0)
        near_high = _f(pick.get("near_high"), 0.0)
        dislocation_score = _f(pick.get("dislocation_score"), 0.0)
        trade_density = _f(pick.get("trade_density"), 0.0)
        range_pct_24h = _f(pick.get("range_pct_24h"), 0.0)
        drawdown_24h = _f(pick.get("drawdown_24h"), 0.0)
        pick_router = route_crypto_signal(
            pct24=pct24,
            r2=r2,
            r4=r4,
            near_high=near_high,
            dislocation_score=dislocation_score,
            breadth_pos_pct24=breadth,
            realized_vol_pct=_f(regime_controller.get("realized_vol_pct"), 0.0),
        )
        pick_family = str(pick_router.get("preferred_family", "balanced")).lower()

        if edge < gate_min_edge:
            gate_rejects["low_edge"] += 1
            continue
        if preferred_family in {"breakout", "dislocation"} and family_confidence >= 0.57:
            if preferred_family == "breakout" and pick_engine == "dislocation":
                gate_rejects["family_mismatch"] = gate_rejects.get("family_mismatch", 0) + 1
                continue
            if preferred_family == "dislocation" and pick_engine == "breakout" and pick_family != "dislocation":
                gate_rejects["family_mismatch"] = gate_rejects.get("family_mismatch", 0) + 1
                continue
        # Dislocation plays are intentionally oversold — skip the lower-bound pct24
        # filter for them; only cap the upper bound (avoid chasing pumps).
        if pick_engine != "dislocation" and pct24 < gate_min_pct24:
            gate_rejects["low_pct24"] += 1
            continue
        if pct24 > gate_max_pct24:
            gate_rejects["high_pct24_chase"] = gate_rejects.get("high_pct24_chase", 0) + 1
            continue
        if qv < gate_min_qv:
            gate_rejects["low_quote_volume"] += 1
            continue
        if regime == "breakout" and near_high < gate_min_near_high:
            gate_rejects["low_near_high"] += 1
            continue
        if regime == "breakout" and r2 < gate_min_r2:
            gate_rejects["low_r2"] += 1
            continue
        if pick_engine == "dislocation" and dislocation_score < gate_min_dislocation:
            gate_rejects["low_dislocation"] += 1
            continue
        if regime == "breakout" and gate_reentry_cooldown > 0:
            last_exit_cycle = _i(recent_exits.get(sym), -10_000_000)
            if (abs_cycle - last_exit_cycle) < gate_reentry_cooldown:
                gate_rejects["cooldown_reentry"] += 1
                continue
        if drawdown_24h >= gate_bad_tick_drawdown and trade_density < gate_bad_tick_trade_density and range_pct_24h > gate_bad_tick_range:
            gate_rejects["suspicious_bad_tick"] += 1
            continue

        risk_frac = min(max(base_risk + edge * 0.05, 0.02), _f(preset.get("entry_max_risk_fraction"), 0.22))
        diversification_slots = max(slots_left, max(min_diversified_slots - len(held), 1))
        alloc_budget = cash / max(diversification_slots, 1)

        ladder_frac = 0.0
        if str(preset.get("entry_mode", "")).lower() == "capital_ladder":
            t1 = _f(preset.get("ladder_edge_tier1"), 0.22)
            t2 = _f(preset.get("ladder_edge_tier2"), 0.16)
            t3 = _f(preset.get("ladder_edge_tier3"), 0.10)
            f1 = _f(preset.get("ladder_frac_tier1"), 1.00)
            f2 = _f(preset.get("ladder_frac_tier2"), 0.50)
            f3 = _f(preset.get("ladder_frac_tier3"), 0.25)
            ff = _f(preset.get("ladder_frac_floor"), 0.08)

            if edge >= t1:
                ladder_frac = f1
            elif edge >= t2:
                ladder_frac = f2
            elif edge >= t3:
                ladder_frac = f3
            else:
                ladder_frac = ff

            # Top-ranked candidates get explicit first-shot capital priority.
            if pick_idx == 0:
                ladder_frac = max(ladder_frac, _f(preset.get("ladder_top1_frac"), ladder_frac))
            elif pick_idx == 1:
                ladder_frac = max(ladder_frac, _f(preset.get("ladder_top2_frac"), ladder_frac))

        if ladder_frac > 0.0:
            raw_notional = cash * ladder_frac
        else:
            raw_notional = min(cash * risk_frac, alloc_budget)

        recent_prices = history.get(sym, []) if isinstance(history.get(sym, []), list) else []
        estimated_vol = max(
            _recent_volatility(recent_prices),
            abs(r2),
            abs(r4) / 2.0,
            abs(r8) / 4.0,
            abs(pct24) / 8.0,
            0.005,
        )
        vol_scalar = min(max(target_position_vol_pct / max(estimated_vol, target_position_vol_pct * 0.50), vol_scalar_floor), vol_scalar_ceiling)
        uncertainty_scalar = 1.0 / (1.0 + uncertainty_penalty_k * max((estimated_vol / max(target_position_vol_pct, 1e-9)) - 1.0, 0.0))
        confidence_scalar = min(max(edge / top_edge, 0.35), 1.0)

        # Dynamic signal-driven sizing: the engine earned the right to decide how
        # much capital to deploy based on its own signal quality.  The ladder frac
        # is just the *baseline* — the combined signal modifier scales it up or
        # down, giving a wide continuous window instead of fixed bins.
        signal_quality = min(max(vol_scalar * uncertainty_scalar * confidence_scalar, 0.10), 3.0)
        raw_notional = raw_notional * signal_quality
        # Hard cap at configurable ceiling fraction of available cash
        _ladder_ceil = _f(preset.get("ladder_frac_ceiling"), 0.90)
        raw_notional = min(raw_notional, cash * _ladder_ceil)

        single_position_cap_usd = max(equity_basis * max_single_position_pct, _f(preset.get("entry_min_notional_usd"), 25.0))
        gross_heat_remaining_usd = max((equity_basis * max_gross_heat_pct) - current_gross_position_value, 0.0)
        candidate_entries.append(
            {
                "symbol": sym,
                "price": px,
                "pick": pick,
                "edge": edge,
                "trade_density": trade_density,
                "accel": _f(pick.get("accel"), 0.0),
                "r2": _f(pick.get("r2"), 0.0),
                "raw_notional_usd": raw_notional,
                "ladder_frac": ladder_frac,
                "estimated_vol": estimated_vol,
                "vol_scalar": vol_scalar,
                "uncertainty_scalar": uncertainty_scalar,
                "confidence_scalar": confidence_scalar,
                "single_position_cap_usd": single_position_cap_usd,
                "gross_heat_remaining_usd": gross_heat_remaining_usd,
                "max_weight_cap_pct": min(single_position_cap_usd / equity_basis, gross_heat_remaining_usd / equity_basis, max_single_position_pct),
                "expected_return": max(edge, 0.0) * confidence_scalar * regime_confidence_multiplier * max(vol_scalar * uncertainty_scalar, 0.10) * max(_f(pick_router.get("family_confidence"), 0.5), 0.5),
                "engine": pick_engine,
                "signal_family": pick_family,
                "router_state": str(pick_router.get("state", "balanced")),
            }
        )

    optimizer_result = optimize_candidate_weights(
        candidate_entries,
        available_heat_pct=available_heat_pct,
        max_single_position_pct=max_single_position_pct,
        turnover_reference=turnover_reference,
        risk_aversion=optimizer_risk_aversion,
        turnover_penalty=optimizer_turnover_penalty,
    )
    optimized_weights = optimizer_result.get("weights", {}) if isinstance(optimizer_result, dict) else {}

    for candidate in candidate_entries:
        sym = str(candidate.get("symbol", ""))
        px = _f(candidate.get("price"), 0.0)
        pick = candidate.get("pick", {}) if isinstance(candidate.get("pick", {}), dict) else {}
        edge = _f(candidate.get("edge"), 0.0)
        pick_engine = str(candidate.get("engine", regime)).lower()
        optimized_weight_pct = max(_f(optimized_weights.get(sym), 0.0), 0.0)
        single_position_cap_usd = _f(candidate.get("single_position_cap_usd"), 0.0)
        gross_heat_remaining_usd = max((equity_basis * max_gross_heat_pct) - current_gross_position_value, 0.0)
        optimized_notional = equity_basis * optimized_weight_pct
        friction = _execution_friction_rates(preset)
        maker_edge_threshold = _f(preset.get("maker_edge_threshold"), 0.20)
        maker_max_trade_density = _f(preset.get("maker_max_trade_density"), 0.55)
        maker_max_accel = _f(preset.get("maker_max_accel"), 0.015)
        maker_preferred = (
            edge >= maker_edge_threshold
            and _f(candidate.get("trade_density"), 0.0) <= maker_max_trade_density
            and _f(candidate.get("accel"), 0.0) <= maker_max_accel
        )
        buy_route = "maker" if maker_preferred else "taker"
        buy_urgency = _resolve_urgency(edge, _f(candidate.get("trade_density"), 0.0), _f(candidate.get("accel"), 0.0), buy_route)
        buy_fee_rate = _f(friction.get("maker_fee_rate" if maker_preferred else "taker_fee_rate"), 0.0)
        buy_slip = 1.0 + _f(friction.get("slippage_rate"), 0.0)
        affordable_notional = cash / max(1.0 + buy_fee_rate, 1e-9)
        notional = min(optimized_notional, single_position_cap_usd, gross_heat_remaining_usd, affordable_notional, _f(candidate.get("raw_notional_usd"), 0.0))
        if triplet_mode and pick_engine in sleeve_caps_pct:
            sleeve_cap_usd = equity_basis * sleeve_caps_pct[pick_engine]
            sleeve_remaining_usd = max(sleeve_cap_usd - sleeve_notional_by_engine.get(pick_engine, 0.0), 0.0)
            if sleeve_remaining_usd <= 0.0:
                gate_rejects["triplet_sleeve_cap"] += 1
            notional = min(notional, sleeve_remaining_usd)
        notional = max(notional, _f(preset.get("entry_min_notional_usd"), 25.0))
        if notional > single_position_cap_usd + 1e-9:
            gate_rejects["single_position_cap"] += 1
            notional = single_position_cap_usd
        if notional > gross_heat_remaining_usd + 1e-9:
            gate_rejects["gross_heat_cap"] += 1
            notional = gross_heat_remaining_usd
        if notional > cash:
            notional = cash
        if notional < 10.0:
            gate_rejects["skip_notional_too_small"] += 1
            continue

        effective_buy_px = px * buy_slip
        qty = notional / max(effective_buy_px, 1e-12)
        buy_fee = notional * buy_fee_rate
        total_debit = notional + buy_fee
        if total_debit > cash:
            total_debit = cash
            notional = total_debit / max(1.0 + buy_fee_rate, 1e-9)
            buy_fee = total_debit - notional
            qty = notional / max(effective_buy_px, 1e-12)
        cash -= total_debit
        current_gross_position_value += notional
        if pick_engine in sleeve_notional_by_engine:
            sleeve_notional_by_engine[pick_engine] += notional
        positions[sym] = {
            "qty": qty,
            "entry": effective_buy_px,
            "opened_cycle": abs_cycle,
            "regime": pick_engine,
            "engine": pick_engine,
            "edge": edge,
            "entry_reference_price": px,
            "entry_fee_paid_usd": buy_fee,
            "cost_basis_usd": notional + buy_fee,
            "trade_density": _f(candidate.get("trade_density"), 0.0),
        }
        trades += 1
        held.add(sym)
        slots_left -= 1

        ev = {
            "timestamp_utc": now_utc(),
            "cycle": cycle,
            "absolute_cycle": abs_cycle,
            "event_type": "binanceus_paper_fill",
            "side": "buy",
            "symbol": sym,
            "qty": round(qty, 10),
            "fill_price": round(effective_buy_px, 6),
            "mark_price": round(px, 6),
            "notional_usd": round(notional, 4),
            "cost_basis_usd": round(notional + buy_fee, 6),
            "buy_fee_usd": round(buy_fee, 6),
            "execution_route": buy_route,
            "slippage_bps": round(_f(friction.get("slippage_bps"), 0.0), 4),
            "taker_fee_bps": round(_f(friction.get("taker_fee_bps"), 0.0), 4),
            "maker_fee_bps": round(_f(friction.get("maker_fee_bps"), 0.0), 4),
            "action": "BUY",
            "reason": "ranked_entry",
            "regime": pick_engine,
            "edge": round(edge, 6),
            "target_flip": "100x" if edge >= 0.22 else ("10x" if edge >= 0.16 else ("5x" if edge >= 0.10 else "taper")),
            "rationale": {
                "r2": round(_f(pick.get("r2"), 0.0), 6),
                "r4": round(_f(pick.get("r4"), 0.0), 6),
                "r8": round(_f(pick.get("r8"), 0.0), 6),
                "accel": round(_f(pick.get("accel"), 0.0), 6),
                "pct24": round(_f(pick.get("pct24"), 0.0), 6),
                "quote_volume": round(_f(pick.get("quote_volume"), 0.0), 2),
                "drawdown_24h": round(_f(pick.get("drawdown_24h"), 0.0), 6),
                "rebound_impulse": round(_f(pick.get("rebound_impulse"), 0.0), 6),
                "dislocation_score": round(dislocation_score, 6),
                "dislocation_reason": str(pick.get("dislocation_reason", "")),
                "ladder_frac": round(_f(candidate.get("ladder_frac"), 0.0), 6),
                "raw_notional_usd": round(_f(candidate.get("raw_notional_usd"), 0.0), 4),
                "optimized_notional_usd": round(optimized_notional, 4),
                "buy_fee_usd": round(buy_fee, 6),
                "execution_route": buy_route,
                "effective_entry_price": round(effective_buy_px, 6),
                "optimized_weight_pct": round(optimized_weight_pct, 6),
                "estimated_vol_pct": round(_f(candidate.get("estimated_vol"), 0.0), 6),
                "vol_scalar": round(_f(candidate.get("vol_scalar"), 0.0), 6),
                "uncertainty_scalar": round(_f(candidate.get("uncertainty_scalar"), 0.0), 6),
                "confidence_scalar": round(_f(candidate.get("confidence_scalar"), 0.0), 6),
                "single_position_cap_usd": round(single_position_cap_usd, 4),
                "gross_heat_remaining_usd": round(gross_heat_remaining_usd, 4),
                "engine": pick_engine,
                "optimizer_status": str(optimizer_result.get("status", "n/a")),
            },
        }
        bid = px * max(1.0 - (_f(friction.get("slippage_rate"), 0.0) * 0.5), 0.0)
        ask = px * (1.0 + (_f(friction.get("slippage_rate"), 0.0) * 0.5))
        shadow_px, shadow_slip_bps = shadow_runner.simulate_fill(bid, ask, "buy", buy_urgency)
        shadow_runner.append_ledger(
            str(SHADOW_LEDGER_CSV_FILE),
            ShadowFill(
                ts_utc=str(ev.get("timestamp_utc")),
                symbol=sym,
                side="buy",
                qty=round(qty, 10),
                est_fill=round(shadow_px, 6),
                slip_bps=round(shadow_slip_bps, 6),
            ),
        )
        tp_key = "tp_dislocation" if pick_engine == "dislocation" else ("tp_breakout" if pick_engine == "breakout" else ("tp_fallback" if pick_engine == "fallback" else "tp_moon"))
        tp_target = round(effective_buy_px * (1.0 + _f(preset.get(tp_key), 0.018)), 6)
        route_intent = RouteIntent(
            symbol=sym,
            side="buy",
            qty=qty,
            urgency=buy_urgency,
            entry_price=effective_buy_px,
            stop_price=round(effective_buy_px * (1.0 + _f(preset.get("sl"), -0.01)), 6),
            take_profit=tp_target,
            reduce_only=False,
        )
        order_template = order_router.build_primary(route_intent, validate_only=True)
        close_template = order_router.build_close_template(route_intent)
        ev["shadow_fill"] = {"est_fill": round(shadow_px, 6), "slip_bps": round(shadow_slip_bps, 6)}
        ev["order_template"] = order_template
        if close_template is not None:
            ev["close_template"] = close_template
        ledger_hash = trade_ledger.append(
            {
                "timestamp": str(ev.get("timestamp_utc")),
                "symbol": sym,
                "side": "buy",
                "status": "OPEN",
                "execution_mode": buy_route,
                "gate_score": round(edge, 6),
                "entry_price": round(effective_buy_px, 6),
                "qty": round(qty, 10),
                "size_usd": round(notional, 6),
                "round_trip_fee_usd": round(buy_fee, 6),
                "tp_net_bps": round(((_f(route_intent.take_profit, effective_buy_px) / max(effective_buy_px, 1e-9)) - 1.0) * 10000.0, 6),
                "sl_net_bps": round(((_f(route_intent.stop_price, effective_buy_px) / max(effective_buy_px, 1e-9)) - 1.0) * 10000.0, 6),
            }
        )
        audit_event = audit_chain.append("paper_buy", {"symbol": sym, "route": buy_route, "edge": round(edge, 6), "ledger_hash": ledger_hash})
        ev["ledger_hash"] = ledger_hash
        ev["trade_id"] = ledger_hash
        ev["audit_hash"] = audit_event.get("event_hash")
        events.append(ev)

    # Mark-to-market.
    unrealized = 0.0
    gross_position_value = 0.0
    for sym, pos in positions.items():
        qty = _f(pos.get("qty"), 0.0)
        entry = _f(pos.get("entry"), 0.0)
        mark = market_price_map.get(sym, entry)
        gross_position_value += qty * mark
        unrealized += (qty * mark) - (qty * entry)
    equity = cash + gross_position_value

    # Prevent unbounded state growth in long runs.
    if recent_exits:
        min_cycle_keep = abs_cycle - 1000
        recent_exits = {k: v for k, v in recent_exits.items() if _i(v, 0) >= min_cycle_keep}

    if not events:
        events.append(
            {
                "timestamp_utc": now_utc(),
                "cycle": cycle,
                "absolute_cycle": abs_cycle,
                "event_type": "binanceus_paper_mark",
                "action": "HOLD",
                "regime": regime,
            }
        )

    for ev in events:
        append_jsonl(BINANCEUS_PAPER_LEDGER_FILE, ev)

    scoreboard = _update_scoreboard(events)
    _write_investor_scorecard(
        scoreboard=scoreboard,
        equity_usd=equity,
        seed_usd=seed_capital,
        abs_cycle=abs_cycle,
        profile=profile,
    )
    totals = scoreboard.get("totals", {}) if isinstance(scoreboard, dict) else {}

    tune_event = "none"
    if _i(totals.get("n"), 0) >= 12 and cycle % 5 == 0:
        wr = _f(totals.get("win_rate"), 0.0)
        pf = _f(totals.get("profit_factor"), 0.0)
        if wr >= 0.57 and pf >= 1.25:
            base_risk = min(base_risk * 1.08, 0.18)
            max_positions = min(max_positions + 1, max(_i(preset.get("max_positions"), 8) + 2, 4))
            tune_event = "risk_up"
        elif wr <= 0.45 or pf <= 0.90:
            base_risk = max(base_risk * 0.90, 0.02)
            max_positions = max(max_positions - 1, 3)
            tune_event = "risk_down"

    primary_event = events[-1]
    state.update(
        {
            "last_tick_utc": now_utc(),
            "absolute_cycle": abs_cycle,
            "initial_cash_usd": round(_f(state.get("initial_cash_usd"), _f(default_state.get("initial_cash_usd"), cash)), 6),
            "seed_capital_usd": round(_f(state.get("seed_capital_usd"), _f(default_state.get("seed_capital_usd"), cash)), 6),
            "cash_usd": round(cash, 6),
            "realized_pnl_usd": round(realized, 6),
            "unrealized_pnl_usd": round(unrealized, 6),
            "equity_usd": round(equity, 6),
            "peak_equity_usd": round(max(_f(state.get("peak_equity_usd"), equity), equity), 6),
            "gross_position_value_usd": round(gross_position_value, 6),
            "trade_count": trades,
            "wins": wins,
            "losses": losses,
            "last_action": primary_event.get("action", "HOLD"),
            "last_price": price,
            "positions": positions,
            "recent_exits": recent_exits,
            "history": history,
            "last_regime": regime,
            "profile": profile_key,
            "hybrid_weight": round(hybrid_weight, 6),
            "breadth_pos_pct24": round(breadth, 6),
            "last_candidates": picks,
            "scan_count": scored.get("scan_count", 0),
            "scan_target": int(max_scan),
            "scored_count": scored.get("scored_count", 0),
            "venue_counts": venue_counts,
            "base_risk_fraction": round(base_risk, 6),
            "max_positions": int(max_positions),
            "capital_tank": {
                "cash_usd": round(cash, 6),
                "equity_usd": round(equity, 6),
                "heat_pct": round((gross_position_value / equity) if equity > 0 else 0.0, 6),
                "deployable_cash_pct": round((cash / equity) if equity > 0 else 0.0, 6),
                "positions_open": len(positions),
                "triplet_mode": bool(triplet_mode),
                "sleeve_notional_usd": {k: round(_f(v, 0.0), 6) for k, v in sleeve_notional_by_engine.items()},
                "sleeve_caps_pct": {k: round(_f(v, 0.0), 6) for k, v in sleeve_caps_pct.items()},
            },
            "adaptive_tuning": {
                "event": tune_event,
                "totals_n": _i(totals.get("n"), 0),
                "totals_win_rate": round(_f(totals.get("win_rate"), 0.0), 6),
                "totals_profit_factor": round(_f(totals.get("profit_factor"), 0.0), 6),
                "base_risk_fraction": round(base_risk, 6),
                "max_positions": int(max_positions),
            },
            "scientific_allocator": {
                "mode": allocator_mode,
                "optimizer_ok": bool(optimizer_result.get("ok", False)) if isinstance(optimizer_result, dict) else False,
                "optimizer_status": str(optimizer_result.get("status", "n/a")) if isinstance(optimizer_result, dict) else "n/a",
                "optimizer_solver": optimizer_result.get("solver") if isinstance(optimizer_result, dict) else None,
                "optimizer_risk_aversion": round(optimizer_risk_aversion, 6),
                "optimizer_turnover_penalty": round(optimizer_turnover_penalty, 6),
                "max_single_position_pct": round(max_single_position_pct, 6),
                "max_gross_heat_pct": round(max_gross_heat_pct, 6),
                "target_position_vol_pct": round(target_position_vol_pct, 6),
                "uncertainty_penalty_k": round(uncertainty_penalty_k, 6),
                "min_diversified_slots": int(min_diversified_slots),
                "vol_scalar_floor": round(vol_scalar_floor, 6),
                "vol_scalar_ceiling": round(vol_scalar_ceiling, 6),
                "equity_basis_usd": round(equity_basis, 6),
                "available_heat_pct": round(available_heat_pct, 6),
                "current_heat_pct": round((gross_position_value / equity) if equity > 0 else 0.0, 6),
                "current_gross_heat_usd": round(gross_position_value, 6),
                "last_target_weights": {str(k): round(_f(v, 0.0), 6) for k, v in optimized_weights.items()},
            },
            "regime_controller": regime_controller,
            "quality_gate": {
                "entry_mode": str(preset.get("entry_mode", "risk_budget")),
                "min_edge": round(gate_min_edge, 6),
                "min_pct24": round(gate_min_pct24, 6),
                "max_pct24": round(gate_max_pct24, 6),
                "min_quote_volume_usd": round(gate_min_qv, 2),
                "min_near_high": round(gate_min_near_high, 6),
                "min_r2": round(gate_min_r2, 6),
                "min_dislocation_score": round(gate_min_dislocation, 6),
                "bad_tick_drawdown_threshold": round(gate_bad_tick_drawdown, 6),
                "bad_tick_trade_density_threshold": round(gate_bad_tick_trade_density, 6),
                "bad_tick_range_threshold": round(gate_bad_tick_range, 6),
                "max_drawdown_halt_pct": round(drawdown_halt_pct, 6),
                "current_drawdown_pct": round(current_drawdown_pct, 6),
                "venue_health_multiplier": round(venue_health_multiplier, 6),
                "reentry_cooldown_cycles": int(gate_reentry_cooldown),
                "execution_friction": _execution_friction_rates(preset),
                "external_intel": {
                    "risk_multiplier": round(_f(external_intel.get("risk_multiplier"), 1.0), 6),
                    "scan_multiplier": round(_f(external_intel.get("scan_multiplier"), 1.0), 6),
                    "preferred_regime": str(external_intel.get("preferred_regime", "")),
                    "preferred_family": str(external_intel.get("preferred_family", "")),
                    "preferred_symbol": str(external_intel.get("preferred_symbol", "")),
                },
                "rejections": gate_rejects,
            },
        }
    )

    save_json(BINANCEUS_PAPER_STATE_FILE, state)

    return {
        "ok": True,
        "state_file": str(BINANCEUS_PAPER_STATE_FILE),
        "ledger_file": str(BINANCEUS_PAPER_LEDGER_FILE),
        "event": primary_event,
        "events_count": len(events),
        "state": state,
        "regime": regime,
        "profile": profile_key,
        "hybrid_weight": hybrid_weight,
        "breadth_pos_pct24": breadth,
        "scan_count": scored.get("scan_count", 0),
        "scan_target": int(max_scan),
        "scored_count": scored.get("scored_count", 0),
        "venue_counts": venue_counts,
        "moon_top": moon_top[:5],
        "fallback_top": fallback_top[:5],
        "dislocation_top": dislocation_top[:5],
        "hybrid_top": hybrid_ranked[:5],
        "quality_gate": {
            "entry_mode": str(preset.get("entry_mode", "risk_budget")),
            "min_edge": gate_min_edge,
            "min_pct24": gate_min_pct24,
            "max_pct24": gate_max_pct24,
            "min_quote_volume_usd": gate_min_qv,
            "min_near_high": gate_min_near_high,
            "min_r2": gate_min_r2,
            "min_dislocation_score": gate_min_dislocation,
            "bad_tick_drawdown_threshold": gate_bad_tick_drawdown,
            "bad_tick_trade_density_threshold": gate_bad_tick_trade_density,
            "bad_tick_range_threshold": gate_bad_tick_range,
            "max_drawdown_halt_pct": drawdown_halt_pct,
            "current_drawdown_pct": current_drawdown_pct,
            "venue_health_multiplier": venue_health_multiplier,
            "reentry_cooldown_cycles": gate_reentry_cooldown,
            "execution_friction": _execution_friction_rates(preset),
            "external_intel": {
                "risk_multiplier": _f(external_intel.get("risk_multiplier"), 1.0),
                "scan_multiplier": _f(external_intel.get("scan_multiplier"), 1.0),
                "preferred_regime": str(external_intel.get("preferred_regime", "")),
                "preferred_family": str(external_intel.get("preferred_family", "")),
                "preferred_symbol": str(external_intel.get("preferred_symbol", "")),
            },
            "rejections": gate_rejects,
        },
        "scientific_allocator": state.get("scientific_allocator", {}),
        "regime_controller": state.get("regime_controller", {}),
        "scoreboard_file": str(BINANCEUS_PAPER_SCOREBOARD_FILE),
        "scoreboard_totals": totals,
    }


def _resolve_alpaca_paper_base() -> str:
    paper_override = os.getenv("ALPACA_PAPER_BASE_URL", "").strip()
    generic_override = os.getenv("ALPACA_BASE_URL", "").strip() or os.getenv(
        "ALPACA_TRADING_BASE_URL", ""
    ).strip()
    if generic_override and not paper_override:
        raise PaperEndpointError(
            "generic Alpaca endpoint overrides require an explicit approved paper origin"
        )
    resolved = normalize_paper_trading_base(paper_override)
    if resolved != PAPER_TRADING_ORIGIN:
        raise PaperEndpointError("Alpaca trading origin is not the approved paper origin")
    return resolved


def alpaca_snapshot() -> Dict[str, Any]:
    try:
        base = _resolve_alpaca_paper_base()
    except PaperEndpointError as exc:
        return {"ok": False, "error": f"paper_origin_blocked:{exc}", "base_url": None}

    key = os.getenv("ALPACA_API_KEY", "").strip()
    secret = os.getenv("ALPACA_API_SECRET", "").strip()

    if not key or not secret:
        return {"ok": False, "error": "Missing ALPACA_API_KEY/ALPACA_API_SECRET", "base_url": base}

    res = _alpaca_request("GET", base, "/v2/account", key, secret, timeout=12)
    if not res.get("ok"):
        return {"ok": False, "base_url": base, "error": res.get("error")}
    data = res.get("data", {})

    def _f(v: Any) -> float | None:
        try:
            return float(v)
        except Exception:
            return None

    return {
        "ok": True,
        "base_url": base,
        "status": data.get("status"),
        "equity": _f(data.get("equity")),
        "cash": _f(data.get("cash")),
        "buying_power": _f(data.get("buying_power")),
    }


def _alpaca_crypto_symbol(unified_symbol: str) -> str:
    sym = str(unified_symbol or "").upper().strip()
    if sym.endswith("USDT"):
        return f"{sym[:-4]}/USD"
    if sym.endswith("USDC"):
        return f"{sym[:-4]}/USD"
    if sym.endswith("USD"):
        return f"{sym[:-3]}/USD"
    return ""


def _alpaca_request(
    method: str,
    base_url: str,
    endpoint: str,
    key: str,
    secret: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    headers = {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
    }
    try:
        safe_base = normalize_paper_trading_base(base_url)
        resp = requests.request(
            method=method.upper(),
            url=f"{safe_base}{endpoint}",
            headers=headers,
            params=params or {},
            json=payload,
            timeout=timeout,
            allow_redirects=False,
        )
        if 300 <= int(resp.status_code) < 400:
            return {
                "ok": False,
                "status_code": int(resp.status_code),
                "error": "paper_redirect_blocked",
            }
        if resp.status_code >= 400:
            return {"ok": False, "status_code": resp.status_code, "error": resp.text[:800]}
        data = resp.json() if resp.text else {}
        return {"ok": True, "status_code": resp.status_code, "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _alpaca_supported_crypto_symbols(base_url: str, key: str, secret: str) -> Set[str]:
    res = _alpaca_request("GET", base_url, "/v2/assets", key, secret, params={"asset_class": "crypto", "status": "active"}, timeout=20)
    if not res.get("ok"):
        return set()
    rows = res.get("data", [])
    out: Set[str] = set()
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol", "")).upper().strip()
            tradable = bool(row.get("tradable", False))
            if symbol and tradable:
                out.add(symbol)
    return out


def _alpaca_pick_candidate(candidates: List[Dict[str, Any]], supported: Set[str], min_edge: float) -> Optional[Dict[str, Any]]:
    for row in candidates:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol", "")).upper().strip()
        edge = _f(row.get("hybrid_score", row.get("moon_score", row.get("breakout_score", 0.0))), 0.0)
        ap_symbol = _alpaca_crypto_symbol(sym)
        if not ap_symbol or ap_symbol not in supported:
            continue
        if edge < min_edge:
            continue
        return {
            "unified_symbol": sym,
            "alpaca_symbol": ap_symbol,
            "edge": edge,
            "price": _f(row.get("price"), 0.0),
            "pct24": _f(row.get("pct24"), 0.0),
        }
    return None


def run_alpaca_true_paper_logic(cycle: int, profile: str, preset: Dict[str, Any], binanceus_engine: Dict[str, Any]) -> Dict[str, Any]:
    try:
        base = _resolve_alpaca_paper_base()
    except PaperEndpointError as exc:
        return {"ok": False, "error": f"paper_origin_blocked:{exc}", "base_url": None}

    key = os.getenv("ALPACA_API_KEY", "").strip()
    secret = os.getenv("ALPACA_API_SECRET", "").strip()

    if not key or not secret:
        return {"ok": False, "error": "missing_alpaca_credentials", "base_url": base}

    default_state = {
        "started_utc": now_utc(),
        "profile": profile,
        "initial_cash_usd": 0.0,
        "trade_count": 0,
        "wins": 0,
        "losses": 0,
        "realized_pnl_usd": 0.0,
        "last_action": "HOLD",
        "open_positions": {},
        "last_candidate": {},
    }
    state = load_json(ALPACA_TRUE_PAPER_STATE_FILE, default_state)
    if not isinstance(state, dict):
        state = dict(default_state)

    account_res = _alpaca_request("GET", base, "/v2/account", key, secret)
    if not account_res.get("ok"):
        return {
            "ok": False,
            "error": f"account_fetch_failed:{account_res.get('error')}",
            "base_url": base,
            "state": state,
        }
    account = account_res.get("data", {}) if isinstance(account_res.get("data", {}), dict) else {}
    account_cash = _f(account.get("cash"), 0.0)
    account_equity = _f(account.get("equity"), account_cash)

    positions_res = _alpaca_request("GET", base, "/v2/positions", key, secret)
    positions_rows = positions_res.get("data", []) if positions_res.get("ok") else []
    if not isinstance(positions_rows, list):
        positions_rows = []

    open_positions = state.get("open_positions", {}) if isinstance(state.get("open_positions", {}), dict) else {}

    tp = _f(preset.get("tp_moon"), 0.012)
    sl = _f(preset.get("sl"), -0.010)
    min_edge = _f(preset.get("min_edge"), 0.08)
    entry_min_notional = max(_f(preset.get("entry_min_notional_usd"), 25.0), 20.0)
    entry_frac = min(max(_f(preset.get("entry_max_risk_fraction"), 0.25), 0.05), 0.60)

    events: List[Dict[str, Any]] = []
    action = "HOLD"
    reason = "none"
    entry_error = ""

    # Exit first: lock in real PnL based on live open positions.
    for pos in positions_rows:
        if not isinstance(pos, dict):
            continue
        symbol = str(pos.get("symbol", "")).upper().strip()
        qty = abs(_f(pos.get("qty"), 0.0))
        avg_entry = _f(pos.get("avg_entry_price"), 0.0)
        mark = _f(pos.get("current_price"), avg_entry)
        if qty <= 0.0 or avg_entry <= 0.0:
            continue
        pnl_pct = (mark / avg_entry) - 1.0
        if pnl_pct < tp and pnl_pct > sl:
            continue

        close_side = "sell" if _f(pos.get("qty"), 0.0) > 0 else "buy"
        close_payload = {
            "symbol": symbol,
            "side": close_side,
            "type": "market",
            "time_in_force": "gtc",
            "qty": str(qty),
        }
        order_res = _alpaca_request("POST", base, "/v2/orders", key, secret, payload=close_payload)
        if not order_res.get("ok"):
            continue
        order = order_res.get("data", {}) if isinstance(order_res.get("data", {}), dict) else {}
        fill_price = _f(order.get("filled_avg_price"), mark)
        entry_ref = open_positions.get(symbol, {}) if isinstance(open_positions.get(symbol, {}), dict) else {}
        entry_price = _f(entry_ref.get("entry_price"), avg_entry)
        realized_pnl = (fill_price - entry_price) * qty

        state["trade_count"] = _i(state.get("trade_count"), 0) + 1
        state["realized_pnl_usd"] = _f(state.get("realized_pnl_usd"), 0.0) + realized_pnl
        if realized_pnl >= 0.0:
            state["wins"] = _i(state.get("wins"), 0) + 1
        else:
            state["losses"] = _i(state.get("losses"), 0) + 1
        open_positions.pop(symbol, None)

        action = "SELL"
        reason = "tp_or_sl"
        events.append(
            {
                "timestamp_utc": now_utc(),
                "cycle": cycle,
                "event_type": "alpaca_true_paper_fill",
                "side": "sell",
                "symbol": symbol,
                "qty": round(qty, 10),
                "fill_price": round(fill_price, 8),
                "entry_price": round(entry_price, 8),
                "pnl_usd": round(realized_pnl, 8),
                "order_id": str(order.get("id", "")),
                "status": str(order.get("status", "unknown")),
                "source": "alpaca_paper_api",
                "truth": "real_fill_path",
            }
        )

    # Entry: use top ranked multi-exchange candidates, but execute only on Alpaca-supported symbols.
    candidates = []
    if isinstance(binanceus_engine, dict):
        candidates = binanceus_engine.get("hybrid_top", [])
        if not isinstance(candidates, list):
            candidates = []
    supported = _alpaca_supported_crypto_symbols(base, key, secret)
    pick = _alpaca_pick_candidate(candidates, supported, min_edge=min_edge)

    has_open = any(abs(_f(pos.get("qty"), 0.0)) > 0.0 for pos in open_positions.values() if isinstance(pos, dict))
    if not has_open and pick is not None:
        notional = min(max(account_cash * entry_frac, entry_min_notional), account_cash)
        if notional >= entry_min_notional:
            buy_payload = {
                "symbol": pick["alpaca_symbol"],
                "side": "buy",
                "type": "market",
                "time_in_force": "gtc",
                "notional": f"{notional:.2f}",
            }
            order_res = _alpaca_request("POST", base, "/v2/orders", key, secret, payload=buy_payload)
            if order_res.get("ok"):
                order = order_res.get("data", {}) if isinstance(order_res.get("data", {}), dict) else {}
                fill_price = _f(order.get("filled_avg_price"), pick.get("price", 0.0))
                qty = _f(order.get("filled_qty"), 0.0)
                if qty <= 0.0 and fill_price > 0.0:
                    qty = notional / fill_price
                open_positions[pick["alpaca_symbol"]] = {
                    "entry_price": fill_price,
                    "qty": qty,
                    "opened_cycle": cycle,
                    "order_id": str(order.get("id", "")),
                    "edge": _f(pick.get("edge"), 0.0),
                }
                action = "BUY"
                reason = "ranked_entry"
                events.append(
                    {
                        "timestamp_utc": now_utc(),
                        "cycle": cycle,
                        "event_type": "alpaca_true_paper_fill",
                        "side": "buy",
                        "symbol": pick["alpaca_symbol"],
                        "qty": round(qty, 10),
                        "fill_price": round(fill_price, 8),
                        "notional_usd": round(notional, 6),
                        "edge": round(_f(pick.get("edge"), 0.0), 6),
                        "pct24": round(_f(pick.get("pct24"), 0.0), 6),
                        "order_id": str(order.get("id", "")),
                        "status": str(order.get("status", "unknown")),
                        "source": "alpaca_paper_api",
                        "truth": "real_fill_path",
                    }
                )
            else:
                entry_error = f"buy_order_failed:{order_res.get('error', 'unknown')}"
        else:
            entry_error = f"insufficient_notional:cash={account_cash:.6f}:min={entry_min_notional:.6f}"
    elif not has_open and pick is None:
        entry_error = "no_supported_candidate_above_edge_gate"

    if not events:
        events.append(
            {
                "timestamp_utc": now_utc(),
                "cycle": cycle,
                "event_type": "alpaca_true_paper_mark",
                "action": "HOLD",
                "source": "alpaca_paper_api",
                "reason": reason,
                "entry_error": entry_error,
            }
        )

    for ev in events:
        append_jsonl(ALPACA_TRUE_PAPER_LEDGER_FILE, ev)

    state.update(
        {
            "last_tick_utc": now_utc(),
            "profile": profile,
            "initial_cash_usd": _f(state.get("initial_cash_usd"), account_cash) if _f(state.get("initial_cash_usd"), 0.0) > 0.0 else account_cash,
            "last_action": action,
            "last_reason": reason,
            "last_error": entry_error,
            "cash_usd": round(account_cash, 6),
            "equity_usd": round(account_equity, 6),
            "open_positions": open_positions,
            "last_candidate": pick or {},
            "supported_symbol_count": len(supported),
            "data_truth_mode": "alpaca_paper_real_orders",
        }
    )
    save_json(ALPACA_TRUE_PAPER_STATE_FILE, state)

    return {
        "ok": True,
        "base_url": base,
        "state": state,
        "event": events[-1],
        "events_count": len(events),
        "positions_count": len(open_positions),
        "supported_symbol_count": len(supported),
        "ledger_file": str(ALPACA_TRUE_PAPER_LEDGER_FILE),
        "state_file": str(ALPACA_TRUE_PAPER_STATE_FILE),
    }


def run_alpaca_builder(python_exe: str) -> Dict[str, Any]:
    script = CODE / "alpaca_paper_loop_builder.py"
    if not script.exists():
        return {"ok": False, "error": f"Missing script: {script}"}

    try:
        proc = subprocess.run(
            [python_exe, str(script)],
            cwd=str(CODE),
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "return_code": proc.returncode,
            "stdout_tail": (proc.stdout or "").splitlines()[-6:],
            "stderr_tail": (proc.stderr or "").splitlines()[-6:],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_institutional_crypto_dashboard_builder(python_exe: str) -> Dict[str, Any]:
    script = CODE / "execution" / "build_institutional_crypto_paper_dashboard.py"
    if not script.exists():
        return {"ok": False, "error": f"Missing script: {script}"}

    try:
        proc = subprocess.run(
            [python_exe, str(script)],
            cwd=str(CODE),
            capture_output=True,
            text=True,
            check=False,
        )
        result = {
            "ok": proc.returncode == 0,
            "return_code": proc.returncode,
            "stdout_tail": (proc.stdout or "").splitlines()[-6:],
            "stderr_tail": (proc.stderr or "").splitlines()[-6:],
            "dashboard_file": str(INSTITUTIONAL_PAPER_DASHBOARD_FILE),
        }
        fallback = ROOT / "dashboard" / "alpaca_paper_live_dashboard.html"
        if not result["ok"] and fallback.exists():
            INSTITUTIONAL_PAPER_DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
            INSTITUTIONAL_PAPER_DASHBOARD_FILE.write_bytes(fallback.read_bytes())
            result.update(
                {
                    "ok": True,
                    "fallback_used": True,
                    "fallback_source": str(fallback),
                    "panel_export_return_code": proc.returncode,
                }
            )
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc), "dashboard_file": str(INSTITUTIONAL_PAPER_DASHBOARD_FILE)}


def run_institutional_crypto_brief_builder(python_exe: str) -> Dict[str, Any]:
    script = CODE / "execution" / "build_institutional_crypto_executive_brief.py"
    if not script.exists():
        return {"ok": False, "error": f"Missing script: {script}"}

    try:
        proc = subprocess.run(
            [python_exe, str(script)],
            cwd=str(CODE),
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "return_code": proc.returncode,
            "stdout_tail": (proc.stdout or "").splitlines()[-8:],
            "stderr_tail": (proc.stderr or "").splitlines()[-8:],
            "brief_file": str(INSTITUTIONAL_PAPER_BRIEF_FILE),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "brief_file": str(INSTITUTIONAL_PAPER_BRIEF_FILE)}


def tick(python_exe: str, cycle: int, profile: str, seed_capital: float, reset_state: bool = False) -> Dict[str, Any]:
    hydrate = hydrate_live_keys()
    runtime_guard = force_paper_mode()

    kraken = kraken_snapshot()
    binance = binance_snapshot("https://api.binance.com")
    binanceus = binance_snapshot("https://api.binance.us")
    binanceus_private = binanceus_private_account_snapshot()
    binanceus_paper = run_binanceus_paper_logic(binanceus.get("price"), cycle, profile, seed_capital, reset_state=reset_state)
    alpaca = alpaca_snapshot()
    profile_key = profile if profile in PROFILE_PRESETS else DEFAULT_PROFILE
    preset = PROFILE_PRESETS.get(profile_key, PROFILE_PRESETS[DEFAULT_PROFILE])
    alpaca_true = run_alpaca_true_paper_logic(cycle, profile_key, preset, binanceus_paper)
    builder = run_alpaca_builder(python_exe)

    payload = {
        "timestamp_utc": now_utc(),
        "cycle": cycle,
        "profile": profile,
        "seed_capital_usd": round(max(seed_capital, 1000.0), 6),
        "reset_state": bool(reset_state),
        "runtime_guard": runtime_guard,
        "hydrate": hydrate,
        "exchanges": {
            "kraken": kraken,
            "binance": binance,
            "binanceus": binanceus,
            "binanceus_private": binanceus_private,
            "alpaca_paper": alpaca,
        },
        "binanceus_paper_engine": binanceus_paper,
        "alpaca_true_paper_engine": alpaca_true,
        "alpaca_builder": builder,
    }
    save_json(STATUS_FILE, payload)
    append_jsonl(LEDGER_FILE, payload)
    payload["institutional_crypto_paper_report"] = build_institutional_crypto_paper_report(payload, seed_capital, reset_state)
    payload["institutional_crypto_dashboard"] = run_institutional_crypto_dashboard_builder(python_exe)
    payload["institutional_crypto_brief"] = run_institutional_crypto_brief_builder(python_exe)
    save_json(STATUS_FILE, payload)
    return payload


def pretty_tick(payload: Dict[str, Any]) -> str:
    ts = payload.get("timestamp_utc", "")
    cycle = payload.get("cycle", "?")
    ex = payload.get("exchanges", {})
    alp_true = payload.get("alpaca_true_paper_engine", {}) if isinstance(payload, dict) else {}

    def fmt(name: str, key: str = "price") -> str:
        item = ex.get(name, {}) if isinstance(ex, dict) else {}
        if not isinstance(item, dict):
            return f"{name}=ERR"
        if item.get("ok"):
            val = item.get(key)
            return f"{name}={val}"
        return f"{name}=ERR"

    return (
        f"[PAPER-TICK] {ts} cycle={cycle} "
        f"profile={payload.get('profile')} "
        f"seed={payload.get('seed_capital_usd')} "
        f"{fmt('kraken')} {fmt('binance')} {fmt('binanceus')} "
        f"bus_priv_ok={ex.get('binanceus_private', {}).get('ok')} "
        f"bus_regime={payload.get('binanceus_paper_engine', {}).get('regime')} "
        f"bus_scan={payload.get('binanceus_paper_engine', {}).get('scan_count')} "
        f"bus_scored={payload.get('binanceus_paper_engine', {}).get('scored_count')} "
        f"bus_open={len(payload.get('binanceus_paper_engine', {}).get('state', {}).get('positions', {}))} "
        f"bus_paper_eq={payload.get('binanceus_paper_engine', {}).get('state', {}).get('equity_usd')} "
        f"bus_last={payload.get('binanceus_paper_engine', {}).get('event', {}).get('action')} "
        f"alpaca_equity={ex.get('alpaca_paper', {}).get('equity')} "
        f"alp_true_ok={alp_true.get('ok')} "
        f"alp_true_last={alp_true.get('event', {}).get('side', alp_true.get('event', {}).get('action'))} "
        f"alp_true_pos={alp_true.get('positions_count')} "
        f"builder_ok={payload.get('alpaca_builder', {}).get('ok')}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-exchange live-ticking paper supervisor")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between cycles")
    parser.add_argument("--cycles", type=int, default=0, help="0 means run forever")
    parser.add_argument("--profile", type=str, default=DEFAULT_PROFILE, choices=sorted(PROFILE_PRESETS.keys()), help="Execution profile preset")
    parser.add_argument("--seed-capital", type=float, default=10000.0, help="Initial paper capital when creating or resetting state")
    parser.add_argument("--reset-paper-state", action="store_true", help="Reset paper state to the requested seeded capital before the next cycle")
    args = parser.parse_args()

    lock_ok, lock_msg = acquire_single_instance_lock(args.profile)
    if not lock_ok:
        print(f"[LOCK] multi_exchange_paper_ticker already running ({lock_msg})", flush=True)
        return 1
    atexit.register(release_single_instance_lock)

    python_exe = sys.executable
    count = 0
    while True:
        if not is_current_lock_owner():
            print("[LOCK] lock ownership lost; exiting duplicate/non-owner process", flush=True)
            return 1

        count += 1
        payload = tick(python_exe, count, args.profile, args.seed_capital, reset_state=(args.reset_paper_state and count == 1))
        print(pretty_tick(payload), flush=True)

        if args.cycles > 0 and count >= args.cycles:
            break
        time.sleep(max(float(args.interval), 1.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
