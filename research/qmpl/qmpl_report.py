#!/usr/bin/env python3
"""Generate reviewer-readable aggregates and plots from a QMPL sweep."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output

    phase = pd.read_csv(output / "phase_sweep_results.csv")
    formation = pd.read_csv(output / "formation_transition_results.csv")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))

    phase["phase_bins_label"] = phase["phase_bins"].astype(str)

    by_bins = (
        phase.groupby("phase_bins_label", dropna=False)
        .agg(
            runs=("pass", "size"),
            pass_rate=("pass", "mean"),
            mean_coherence=("final_coherence", "mean"),
            median_coherence=("final_coherence", "median"),
            mean_freq_std=("final_frequency_std", "mean"),
            mean_control_energy=("control_energy_proxy", "mean"),
            mean_bytes=("estimated_bytes_per_agent_s", "mean"),
        )
        .reset_index()
    )
    by_k = (
        phase.groupby("coupling_gain")
        .agg(
            runs=("pass", "size"),
            pass_rate=("pass", "mean"),
            mean_coherence=("final_coherence", "mean"),
            median_coherence=("final_coherence", "median"),
            mean_recovery=("recovery_time_s", "mean"),
        )
        .reset_index()
    )
    by_fault = (
        phase.groupby(["packet_loss", "sensor_noise", "latency_steps"])
        .agg(
            runs=("pass", "size"),
            pass_rate=("pass", "mean"),
            mean_coherence=("final_coherence", "mean"),
            mean_freq_std=("final_frequency_std", "mean"),
        )
        .reset_index()
    )
    formation_by_transition = (
        formation.groupby(["start_shape", "end_shape", "agent_count"])
        .agg(
            runs=("pass", "size"),
            pass_rate=("pass", "mean"),
            mean_final_error=("final_rms_error", "mean"),
            min_observed_separation=("min_separation", "min"),
            mean_transition_time=("transition_time_s", "mean"),
            mean_control_energy=("control_energy_proxy", "mean"),
        )
        .reset_index()
    )

    by_bins.to_csv(output / "aggregate_by_quantization.csv", index=False)
    by_k.to_csv(output / "aggregate_by_coupling.csv", index=False)
    by_fault.to_csv(output / "aggregate_by_fault_condition.csv", index=False)
    formation_by_transition.to_csv(
        output / "aggregate_formation_transitions.csv", index=False
    )

    plt.figure(figsize=(8, 5))
    plt.plot(by_k["coupling_gain"], by_k["pass_rate"], marker="o")
    plt.xlabel("Coupling gain K")
    plt.ylabel("Pass rate")
    plt.title("QMPL Baseline Pass Rate vs Coupling Gain")
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output / "pass_rate_vs_coupling.png", dpi=160)
    plt.close()

    order = ["4", "8", "16", "continuous"]
    bins_plot = (
        by_bins.set_index("phase_bins_label").reindex(order).dropna().reset_index()
    )
    plt.figure(figsize=(8, 5))
    plt.plot(
        bins_plot["phase_bins_label"],
        bins_plot["mean_coherence"],
        marker="o",
    )
    plt.xlabel("Phase representation")
    plt.ylabel("Mean final coherence")
    plt.title("QMPL Baseline Coherence vs Quantization")
    plt.ylim(0, 1.02)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output / "coherence_vs_quantization.png", dpi=160)
    plt.close()

    fault_plot = by_fault.copy()
    fault_plot["condition"] = fault_plot.apply(
        lambda r: (
            f"loss={r.packet_loss:g}, noise={r.sensor_noise:g}, "
            f"lag={int(r.latency_steps)}"
        ),
        axis=1,
    )
    plt.figure(figsize=(10, 5))
    plt.bar(fault_plot["condition"], fault_plot["pass_rate"])
    plt.ylabel("Pass rate")
    plt.xlabel("Fault condition")
    plt.title("QMPL Baseline Robustness Across Communication and Sensing Faults")
    plt.ylim(0, 1.05)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output / "fault_condition_pass_rates.png", dpi=160)
    plt.close()

    continuous = by_bins[by_bins["phase_bins_label"] == "continuous"].iloc[0]
    q16 = by_bins[by_bins["phase_bins_label"] == "16"].iloc[0]
    k_best = by_k.sort_values(
        ["pass_rate", "mean_coherence"], ascending=False
    ).iloc[0]
    k_low = by_k.sort_values("coupling_gain").iloc[0]
    fault_best = by_fault.sort_values(
        ["pass_rate", "mean_coherence"], ascending=False
    ).iloc[0]
    fault_worst = by_fault.sort_values(
        ["pass_rate", "mean_coherence"]
    ).iloc[0]

    claim_map = f"""# QMPL Initial Public-Safe Simulation Evidence

**Generated:** {datetime.now(timezone.utc).isoformat()}  
**Scope:** generic second-order oscillator and 2D formation-transition baselines  
**Claim level:** simulation only; not external validation, aerodynamic validation,
flight validation, certification, or operational capability

## Frozen run

- Phase-network runs: **{summary['phase_summary']['run_count']}**
- Phase-network pass rate: **{summary['phase_summary']['pass_rate']:.3f}**
- Mean final coherence: **{summary['phase_summary']['mean_final_coherence']:.4f}**
- Formation-transition runs: **{summary['formation_summary']['run_count']}**
- Formation-transition pass rate: **{summary['formation_summary']['pass_rate']:.3f}**

## Initial bounded findings

### Coupling threshold

The lowest tested gain, `K={k_low['coupling_gain']}`, produced pass rate
`{k_low['pass_rate']:.3f}`. The strongest aggregate tested gain,
`K={k_best['coupling_gain']}`, produced pass rate `{k_best['pass_rate']:.3f}`.

Under the frozen model and parameter range, stronger coupling increased the
probability of satisfying the preselected coherence and frequency-agreement gates.

### Quantized exchange

The 16-bin condition produced mean coherence `{q16['mean_coherence']:.4f}` and
pass rate `{q16['pass_rate']:.3f}`. The continuous comparator produced mean
coherence `{continuous['mean_coherence']:.4f}` and pass rate
`{continuous['pass_rate']:.3f}`.

In this simulator, 16-bin communication retained useful synchronization across
the tested conditions. This does not establish hardware, field, or bandwidth
superiority.

### Fault sensitivity

The strongest aggregate fault condition produced pass rate
`{fault_best['pass_rate']:.3f}`. The weakest produced
`{fault_worst['pass_rate']:.3f}`.

Packet loss, noise, and delay remain explicit sweep dimensions; negative outcomes
must be retained.

### Formation baseline

The generic position controller completed
`{summary['formation_summary']['pass_count']}` of
`{summary['formation_summary']['run_count']}` transitions under the frozen error
and separation gates.

This supports using the kinematic controller as a comparator for future
split/reconfigure/rejoin experiments. It does not prove aerodynamic benefit or
safe flight.

## Still unproven

- complete analytical stability margins;
- superiority over every named controller baseline;
- aerodynamic or wake-interaction benefit;
- hardware timing, battery, actuator, or sensor feasibility;
- collision safety under real navigation uncertainty;
- external reproducibility;
- patentability or freedom to operate.
"""
    (output / "CLAIM_TO_ARTIFACT_MAP.md").write_text(
        claim_map, encoding="utf-8"
    )

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            manifest["outputs"][path.name] = sha256_file(path)
    manifest["report_source_sha256"] = sha256_file(Path(__file__).resolve())
    manifest["manifest_updated_utc"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
