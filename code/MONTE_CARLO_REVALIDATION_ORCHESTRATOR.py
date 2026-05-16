"""
MONTE_CARLO_REVALIDATION_ORCHESTRATOR.py
=========================================
Re-validate all 20+ sectors using new historical outage data.
Runs Monte Carlo simulations to generate updated Sharpe baselines.
Computes opportunity gains vs. current deployment baseline.

Execution: python MONTE_CARLO_REVALIDATION_ORCHESTRATOR.py --iterations 10000
Output: out/monte_carlo_validation_<UTCSTAMP>.json
    out/monte_carlo_validation_latest.json
        out/sector_sharpe_baselines_updated.json
        out/opportunity_gain_matrix_updated.json
"""

import argparse
import json
import os
import random
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# ================================================================
# CONFIG
# ================================================================
ROOT = Path(os.getenv("LUMA_ROOT", str(Path(__file__).resolve().parents[1]))).resolve()
CONF = ROOT / "config"
OUT  = ROOT / "out"
ASSUMPTIONS_PATH = CONF / "impact_model_assumptions.json"

DEFAULT_IMPACT_ASSUMPTIONS = {
    "historical_years": 20.0,
    "default_savings_pct": 0.32,
    "min_savings_pct": 0.05,
    "max_savings_pct": 0.90,
    "monte_carlo": {
        "default_detection_rate": 0.32,
        "sector_detection_rate_overrides": {},
        "prevention_share_of_detected": 0.60,
        "early_detection_share_of_detected": 0.40,
        "early_detection_loss_reduction_pct": 0.50,
    },
}

# ================================================================
# UTILITIES
# ================================================================
def now_utc():
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def load_json(path: Path, default=None):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load {path}: {e}")
    return default if default is not None else {}

def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    print(f"[OK] Saved: {path.name}")


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def load_impact_assumptions() -> Dict[str, Any]:
    raw = load_json(ASSUMPTIONS_PATH, {})
    assumptions = dict(DEFAULT_IMPACT_ASSUMPTIONS)
    assumptions["monte_carlo"] = dict(DEFAULT_IMPACT_ASSUMPTIONS["monte_carlo"])

    if isinstance(raw, dict):
        assumptions["historical_years"] = max(
            1.0,
            _to_float(raw.get("historical_years"), assumptions["historical_years"]),
        )
        assumptions["default_savings_pct"] = _to_float(
            raw.get("default_savings_pct"), assumptions["default_savings_pct"]
        )
        assumptions["min_savings_pct"] = _to_float(
            raw.get("min_savings_pct"), assumptions["min_savings_pct"]
        )
        assumptions["max_savings_pct"] = _to_float(
            raw.get("max_savings_pct"), assumptions["max_savings_pct"]
        )

        raw_mc = raw.get("monte_carlo")
        if isinstance(raw_mc, dict):
            assumptions["monte_carlo"]["default_detection_rate"] = _to_float(
                raw_mc.get(
                    "default_detection_rate",
                    assumptions["monte_carlo"]["default_detection_rate"],
                ),
                assumptions["monte_carlo"]["default_detection_rate"],
            )
            assumptions["monte_carlo"]["prevention_share_of_detected"] = _to_float(
                raw_mc.get(
                    "prevention_share_of_detected",
                    assumptions["monte_carlo"]["prevention_share_of_detected"],
                ),
                assumptions["monte_carlo"]["prevention_share_of_detected"],
            )
            assumptions["monte_carlo"]["early_detection_share_of_detected"] = _to_float(
                raw_mc.get(
                    "early_detection_share_of_detected",
                    assumptions["monte_carlo"]["early_detection_share_of_detected"],
                ),
                assumptions["monte_carlo"]["early_detection_share_of_detected"],
            )
            assumptions["monte_carlo"]["early_detection_loss_reduction_pct"] = _to_float(
                raw_mc.get(
                    "early_detection_loss_reduction_pct",
                    assumptions["monte_carlo"]["early_detection_loss_reduction_pct"],
                ),
                assumptions["monte_carlo"]["early_detection_loss_reduction_pct"],
            )

            overrides: Dict[str, float] = {}
            raw_overrides = raw_mc.get("sector_detection_rate_overrides")
            if isinstance(raw_overrides, dict):
                for key, value in raw_overrides.items():
                    overrides[str(key)] = _to_float(
                        value,
                        assumptions["monte_carlo"]["default_detection_rate"],
                    )
            assumptions["monte_carlo"]["sector_detection_rate_overrides"] = overrides

    lo = assumptions["min_savings_pct"]
    hi = assumptions["max_savings_pct"]
    if hi < lo:
        lo, hi = hi, lo
    assumptions["min_savings_pct"] = lo
    assumptions["max_savings_pct"] = hi

    mc = assumptions["monte_carlo"]
    mc["default_detection_rate"] = _clamp(mc["default_detection_rate"], lo, hi)
    mc["prevention_share_of_detected"] = _clamp(mc["prevention_share_of_detected"], 0.0, 1.0)
    mc["early_detection_share_of_detected"] = _clamp(mc["early_detection_share_of_detected"], 0.0, 1.0)
    mc["early_detection_loss_reduction_pct"] = _clamp(mc["early_detection_loss_reduction_pct"], 0.0, 1.0)
    mc["sector_detection_rate_overrides"] = {
        k: _clamp(v, lo, hi)
        for k, v in mc.get("sector_detection_rate_overrides", {}).items()
    }
    return assumptions

def compute_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.00) -> float:
    """Compute Sharpe ratio from returns array"""
    if not returns or len(returns) < 2:
        return 0.0
    returns_arr = np.array(returns)
    excess_returns = returns_arr - risk_free_rate
    return np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0.0

def compute_sortino_ratio(returns: List[float], target_return: float = 0.00) -> float:
    """Compute Sortino ratio (penalizes downside only)"""
    if not returns or len(returns) < 2:
        return 0.0
    returns_arr = np.array(returns)
    excess_returns = returns_arr - target_return
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
    return np.mean(excess_returns) / downside_std if downside_std > 0 else np.mean(excess_returns)

def monte_carlo_simulation(
    outages: List[Dict],
    sector: str,
    assumptions: Dict[str, Any],
    iterations: int = 1000,
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation on outage data for a sector.
    Generates realistic scenarios by:
      - Resampling outage frequency
      - Varying loss per event
      - Modeling prevention/detection efficiency improvements
    """
    if not outages:
        return {"sector": sector, "error": "No outages for sector"}
    
    sector_outages = [o for o in outages if o.get("sector") == sector]
    if not sector_outages:
        return {"sector": sector, "error": "No outages for sector"}
    
    simulation_results = {
        "sector": sector,
        "outage_count": len(sector_outages),
        "iterations": iterations,
        "baseline_annual_loss": 0,
        "detected_before_loss": 0,
        "prevented_with_detection": 0,
        "sharpe_baseline": 0,
        "sharpe_with_lumencore": 0,
        "sortino_baseline": 0,
        "sortino_with_lumencore": 0,
        "simulation_runs": [],
    }
    
    historical_years = assumptions["historical_years"]
    mc_assumptions = assumptions["monte_carlo"]
    detection_rate = mc_assumptions["sector_detection_rate_overrides"].get(
        sector,
        mc_assumptions["default_detection_rate"],
    )
    prevention_share = mc_assumptions["prevention_share_of_detected"]
    early_detection_share = mc_assumptions["early_detection_share_of_detected"]
    share_total = prevention_share + early_detection_share
    if share_total > 1.0:
        prevention_share /= share_total
        early_detection_share /= share_total
    early_detection_loss_reduction = mc_assumptions["early_detection_loss_reduction_pct"]

    simulation_results["assumptions"] = {
        "historical_years": historical_years,
        "detection_rate": detection_rate,
        "prevention_share_of_detected": prevention_share,
        "early_detection_share_of_detected": early_detection_share,
        "early_detection_loss_reduction_pct": early_detection_loss_reduction,
    }

    # Calculate baseline loss
    baseline_losses = [o["estimated_loss_usd"] for o in sector_outages]
    baseline_annual_loss = sum(baseline_losses) / historical_years
    simulation_results["baseline_annual_loss"] = baseline_annual_loss
    
    # Run Monte Carlo iterations
    runs = []
    for iteration in range(iterations):
        # Resample outages with variation
        sampled_outages = [random.choice(sector_outages) for _ in range(len(sector_outages))]
        
        # Baseline scenario: all losses realized
        baseline_loss_this_run = sum(o["estimated_loss_usd"] for o in sampled_outages)
        
        # With LumenCore: split detected events into prevented and early-detected reduced-loss events.
        prevented_count = int(len(sampled_outages) * detection_rate * prevention_share)
        detected_early_count = int(len(sampled_outages) * detection_rate * early_detection_share)
        
        loss_with_lumencore = baseline_loss_this_run
        for i in range(prevented_count):
            loss_with_lumencore -= sampled_outages[i]["estimated_loss_usd"]
        for i in range(prevented_count, prevented_count + detected_early_count):
            if i < len(sampled_outages):
                loss_with_lumencore -= sampled_outages[i]["estimated_loss_usd"] * early_detection_loss_reduction
        
        # Calculate return (negative loss is positive return when added to baseline)
        baseline_return = 0  # Baseline is zero-return (loss state)
        lumencore_return = (baseline_loss_this_run - loss_with_lumencore) / baseline_loss_this_run if baseline_loss_this_run > 0 else 0
        
        runs.append({
            "iteration": iteration,
            "baseline_loss": baseline_loss_this_run,
            "predicted_loss_with_lumencore": loss_with_lumencore,
            "savings": baseline_loss_this_run - loss_with_lumencore,
            "savings_pct": (baseline_loss_this_run - loss_with_lumencore) / baseline_loss_this_run if baseline_loss_this_run > 0 else 0,
        })
    
    simulation_results["simulation_runs"] = runs[:10]  # Store first 10 for reference
    
    # Calculate aggregate metrics
    all_baselines = [r["baseline_loss"] for r in runs]
    all_lumencore = [r["predicted_loss_with_lumencore"] for r in runs]
    all_savings_pct = [r["savings_pct"] for r in runs]
    
    # Compute Sharpe ratios (difference between scenarios as a return proxy)
    returns_baseline = [0] * len(runs)  # Baseline is neutral
    returns_lumencore = all_savings_pct  # Savings percentage as return
    
    simulation_results["sharpe_baseline"] = compute_sharpe_ratio(returns_baseline)
    simulation_results["sharpe_with_lumencore"] = compute_sharpe_ratio(returns_lumencore)
    simulation_results["sortino_baseline"] = compute_sortino_ratio(returns_baseline)
    simulation_results["sortino_with_lumencore"] = compute_sortino_ratio(returns_lumencore)
    
    # Summary statistics
    avg_savings = np.mean(all_savings_pct)
    std_savings = np.std(all_savings_pct)
    
    simulation_results["avg_savings_pct"] = float(avg_savings)
    simulation_results["std_savings_pct"] = float(std_savings)
    simulation_results["min_savings_pct"] = float(np.min(all_savings_pct))
    simulation_results["max_savings_pct"] = float(np.max(all_savings_pct))
    simulation_results["confidence_interval_95%"] = [
        float(np.percentile(all_savings_pct, 2.5)),
        float(np.percentile(all_savings_pct, 97.5)),
    ]
    
    return simulation_results

# ================================================================
# SECTOR DEFINITIONS
# ================================================================
SECTORS = [
    "power_grid", "energy", "labor", "weather", "water_hydrology",
    "air_quality", "rates", "market_data", "macro", "demographic",
    "economic_macro", "market_execution", "crypto_exec", "broker",
]

# ================================================================
# MAIN ORCHESTRATOR
# ================================================================
def main(iterations: int = 1000):
    print("\n" + "=" * 80)
    print("MONTE CARLO REVALIDATION ORCHESTRATOR")
    print("=" * 80)
    print(f"Start: {now_utc()}")
    print(f"Iterations per Sector: {iterations:,}")
    
    # Load ingested data
    assumptions = load_impact_assumptions()
    ingestion_data = load_json(OUT / "master_data_ingestion_proof.json")
    outages_data = load_json(OUT / "historical_facility_outages_normalized.json")
    sector_impact_data = load_json(OUT / "sector_economic_impact_matrix.json")
    
    all_outages = outages_data.get("outages", [])
    print(f"Total Outages Loaded: {len(all_outages)}")
    
    # Run Monte Carlo for each sector
    all_results = {
        "orchestrator": {
            "started": now_utc(),
            "version": "1.0",
            "iterations_per_sector": iterations,
            "total_sectors": len(SECTORS),
            "assumptions_path": str(ASSUMPTIONS_PATH),
        },
        "validations": [],
        "summary": {},
    }
    
    print(f"\nRunning Monte Carlo simulations for {len(SECTORS)} sectors...")
    start_time = time.time()
    
    for idx, sector in enumerate(SECTORS):
        print(f"  [{idx+1}/{len(SECTORS)}] {sector:30} ", end="", flush=True)
        tick = time.time()
        
        result = monte_carlo_simulation(
            all_outages,
            sector,
            assumptions=assumptions,
            iterations=iterations,
        )
        all_results["validations"].append(result)
        
        elapsed = time.time() - tick
        sharpe_with_lumencore = result.get("sharpe_with_lumencore", 0)
        avg_savings = result.get("avg_savings_pct", 0)
        print(f"  [OK] Sharpe={sharpe_with_lumencore:6.2f} | Savings={avg_savings*100:5.1f}% | {elapsed:.1f}s")
    
    elapsed_total = time.time() - start_time
    
    all_results["orchestrator"]["completed"] = now_utc()
    all_results["orchestrator"]["total_compute_time_seconds"] = elapsed_total
    
    # Build summary statistics
    sharpes_with_lumencore = [v.get("sharpe_with_lumencore", 0) for v in all_results["validations"]]
    avg_savings_all = [v.get("avg_savings_pct", 0) for v in all_results["validations"]]
    
    all_results["summary"] = {
        "avg_sharpe_with_lumencore": float(np.mean(sharpes_with_lumencore)),
        "max_sharpe_with_lumencore": float(np.max(sharpes_with_lumencore)),
        "min_sharpe_with_lumencore": float(np.min(sharpes_with_lumencore)),
        "avg_savings_across_sectors": float(np.mean(avg_savings_all)),
        "total_compute_time_minutes": elapsed_total / 60,
    }
    
    # Save results
    validation_path = OUT / f"monte_carlo_validation_{utc_stamp()}.json"
    validation_latest_path = OUT / "monte_carlo_validation_latest.json"
    save_json(validation_path, all_results)
    save_json(validation_latest_path, all_results)
    
    # Build updated Sharpe baselines
    sharpe_baselines = {
        "timestamp": now_utc(),
        "baselines": {},
    }
    for validation in all_results["validations"]:
        sector = validation["sector"]
        sharpe_baselines["baselines"][sector] = {
            "sharpe_ratio": validation.get("sharpe_with_lumencore", 0),
            "sortino_ratio": validation.get("sortino_with_lumencore", 0),
            "avg_savings_pct": validation.get("avg_savings_pct", 0),
        }
    
    baselines_path = OUT / "sector_sharpe_baselines_updated.json"
    save_json(baselines_path, sharpe_baselines)
    
    # Build opportunity gain matrix
    gain_matrix = {
        "timestamp": now_utc(),
        "sectors": {},
    }
    for validation in all_results["validations"]:
        sector = validation["sector"]
        baseline_loss = validation.get("baseline_annual_loss", 0)
        avg_savings_pct = validation.get("avg_savings_pct", 0)
        
        gain_matrix["sectors"][sector] = {
            "baseline_annual_loss_usd": baseline_loss,
            "avg_savings_pct": avg_savings_pct,
            "annual_recoverable_usd": baseline_loss * avg_savings_pct,
            "sharpe_improvement": validation.get("sharpe_with_lumencore", 0),
            "monte_carlo_confidence_95%": validation.get("confidence_interval_95%", [0, 0]),
        }
    
    gain_path = OUT / "opportunity_gain_matrix_updated.json"
    save_json(gain_path, gain_matrix)
    
    print("\n" + "=" * 80)
    print("MONTE CARLO REVALIDATION COMPLETE")
    print("=" * 80)
    print(f"Total Time: {elapsed_total:.1f}s ({elapsed_total/60:.1f} minutes)")
    print(f"Sectors Validated: {len(SECTORS)}")
    print(f"Avg Sharpe Ratio: {all_results['summary']['avg_sharpe_with_lumencore']:.2f}")
    print(f"Avg Savings Potential: {all_results['summary']['avg_savings_across_sectors']*100:.1f}%")
    print(f"\nOutput Files:")
    print(f"  - {validation_path.name}")
    print(f"  - {validation_latest_path.name}")
    print(f"  - {baselines_path.name}")
    print(f"  - {gain_path.name}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monte Carlo Revalidation Orchestrator")
    parser.add_argument("--iterations", type=int, default=1000, help="Iterations per sector (default: 1000)")
    args = parser.parse_args()
    
    main(iterations=args.iterations)
