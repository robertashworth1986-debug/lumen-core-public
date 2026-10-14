"""Descriptive paired-series overlay; supersedes the uploaded stochastic baseline.

The retained filename is historical: these diagnostics do not validate quantum
behavior, intelligence, a Lyapunov exponent or a causal intervention.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import scipy
from scipy.signal import welch

from research_artifact_io import (
    BOUNDARY, csv_columns, increasing, new_report, plotting, snapshot, write_manifest,
)

FIELDS = ("t", "energy", "stability", "error")


def load_series(raw):
    data = csv_columns(raw, FIELDS, minimum=8)
    increasing(data["t"], uniform=True)
    if np.any(data["error"] < 0):
        raise ValueError("error must be a nonnegative loss")
    return data


def summarize(data):
    spacing = increasing(data["t"], uniform=True)
    frequency, power = welch(data["energy"], fs=1.0 / spacing,
                             nperseg=min(256, len(data["t"])))
    total = float(power.sum())
    if not np.isfinite(power).all() or not np.isfinite(total):
        raise ValueError("spectral computation overflowed")
    entropy = peak = None
    if total > 0:
        probabilities = power[power > 0] / total
        entropy = float(-np.sum(probabilities * np.log(probabilities)) / np.log(len(power)))
        peak = float(power.max() / total)
    metrics = {
        "sample_count": len(data["t"]), "sample_spacing": spacing,
        "median_stability": float(np.median(data["stability"])),
        "integrated_error": float(np.trapezoid(data["error"], data["t"])),
        "normalized_spectral_entropy": entropy,
        "spectral_peak_power_fraction": peak,
    }
    if any(v is not None and not np.isfinite(v) for v in metrics.values()):
        raise ValueError("metric computation overflowed")
    return metrics, frequency, power


def compare(candidate_raw, baseline_raw):
    candidate, baseline = load_series(candidate_raw), load_series(baseline_raw)
    if not np.array_equal(candidate["t"], baseline["t"]):
        raise ValueError("candidate and baseline require identical paired timestamps")
    cm, _, _ = summarize(candidate)
    bm, _, _ = summarize(baseline)
    deltas = {key: (None if cm[key] is None or bm[key] is None else cm[key] - bm[key])
              for key in cm if key not in {"sample_count", "sample_spacing"}}
    return candidate, baseline, {"candidate": cm, "baseline": bm,
                                "candidate_minus_baseline": deltas}


def build_report(candidate_path, baseline_path, output, *, evidence_type, time_unit):
    cr, br = snapshot(candidate_path), snapshot(baseline_path)
    candidate, baseline, metrics = compare(cr, br)
    plt = plotting()
    with new_report(output) as stage:
        fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        for ax, key in zip(axes, ("energy", "stability", "error")):
            ax.plot(candidate["t"], candidate[key], label="Candidate")
            ax.plot(baseline["t"], baseline[key], label="Supplied baseline", alpha=.75)
            ax.set_ylabel(key + " (source units)")
            ax.legend()
        axes[-1].set_xlabel(f"Time ({time_unit})")
        fig.suptitle(f"Paired descriptive overlay / {evidence_type}")
        fig.tight_layout()
        fig.savefig(stage / "paired_timeseries.png", dpi=150)
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(10, 5))
        for label, data in (("Candidate", candidate), ("Supplied baseline", baseline)):
            _, frequency, power = summarize(data)
            ax.plot(frequency, power, label=label)
        ax.set(xlabel=f"Frequency (cycles per {time_unit})", ylabel="PSD (source units)",
               title="Welch power spectrum / descriptive, not coherence")
        ax.legend()
        fig.tight_layout()
        fig.savefig(stage / "spectrum.png", dpi=150)
        plt.close(fig)
        return write_manifest(stage, {
            "tool": Path(__file__).name, "evidence_type": evidence_type,
            "evidence_type_is_user_supplied": True, "scipy": scipy.__version__,
            "time_unit": time_unit, "metrics": metrics,
            "paired_timestamps_verified": True, "causal_comparability_verified": False,
            "notes": [BOUNDARY, "No baseline is generated or inferred.",
                      "Positive deltas are arithmetic differences, not blanket improvements.",
                      "Spectral metrics are null for zero detrended power.",
                      "Metric definitions, units and matched experimental conditions require source review."],
        }, {"candidate.csv": cr, "baseline.csv": br,
            "source.py": snapshot(__file__), "artifact_io.py": snapshot(Path(__file__).with_name("research_artifact_io.py"))})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-type", choices=("synthetic", "modeled", "replay", "measured", "unknown"), required=True)
    parser.add_argument("--time-unit", required=True)
    args = parser.parse_args(argv)
    build_report(args.candidate, args.baseline, args.output,
                 evidence_type=args.evidence_type, time_unit=args.time_unit)
    print(f"Descriptive report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
