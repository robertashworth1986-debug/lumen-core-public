"""Repair of the truncated geometry report; plots are explicitly illustrative."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from research_artifact_io import (
    BOUNDARY, csv_columns, new_report, plotting, snapshot, write_manifest,
)


def load_geometry(raw):
    return csv_columns(raw, ("D0", "D1", "tau", "score"), minimum=1)


def fibonacci_sphere(n=500):
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least two")
    i = np.arange(n)
    z = 1 - 2 * (i + .5) / n
    radius = np.sqrt(1 - z * z)
    theta = 2 * np.pi * i / ((1 + 5**.5) / 2)
    return radius * np.cos(theta), radius * np.sin(theta), z


def helix():
    t = np.linspace(0, 16 * np.pi, 1200)
    return np.cos(t), np.sin(t), .5 * t / (2 * np.pi)


def log_spiral():
    t = np.linspace(0, 12 * np.pi, 1500)
    radius = .1 * np.exp(.15 * t)
    return radius * np.cos(t), radius * np.sin(t), .25 * radius


def build_report(output, *, csv_path=None, illustrations_only=False):
    if (csv_path is not None) == illustrations_only:
        raise ValueError("choose an explicit CSV or illustrations-only mode")
    raw = snapshot(csv_path) if csv_path is not None else None
    data = load_geometry(raw) if raw is not None else None
    plt = plotting()
    from matplotlib.backends.backend_pdf import PdfPages
    with new_report(output) as stage:
        with PdfPages(stage / "Geometry_Descriptive_Report.pdf") as pdf:
            if data is not None:
                fig = plt.figure(figsize=(10, 7))
                ax = fig.add_subplot(111, projection="3d")
                points = ax.scatter(data["D0"], data["D1"], data["tau"], c=data["score"])
                fig.colorbar(points, ax=ax, shrink=.55).set_label("Supplied score / direction unverified")
                ax.set(xlabel="D0", ylabel="D1", zlabel="tau", title="Supplied geometry samples / source units")
                pdf.savefig(fig)
                plt.close(fig)
            for title, coordinates, scatter in (
                ("Illustrative parametric helix / no magnetic-field calculation", helix(), False),
                ("Illustrative logarithmic spiral on a cone", log_spiral(), False),
                ("Illustrative Fibonacci sphere", fibonacci_sphere(), True),
            ):
                fig = plt.figure(figsize=(10, 7))
                ax = fig.add_subplot(111, projection="3d")
                if scatter:
                    ax.scatter(*coordinates, s=4)
                else:
                    ax.plot(*coordinates)
                ax.set(title=title, xlabel="x (arbitrary units)", ylabel="y (arbitrary units)", zlabel="z (arbitrary units)")
                pdf.savefig(fig)
                plt.close(fig)
            fig = plt.figure(figsize=(10, 7))
            ax = fig.add_subplot(111, projection="3d")
            x, y = np.meshgrid(np.linspace(-3, 3, 100), np.linspace(-3, 3, 100))
            ax.plot_surface(x, y, np.sin(np.sqrt(x*x + y*y)))
            ax.set(title="Illustrative mathematical surface: sin(sqrt(x^2 + y^2))", xlabel="x", ylabel="y", zlabel="z")
            pdf.savefig(fig)
            plt.close(fig)
            fig, ax = plt.subplots(figsize=(10, 7))
            ax.axis("off")
            ax.text(.05, .9, "Geometry report / evidence boundary", fontsize=17)
            ax.text(.05, .78, "Mode: " + ("illustrations only; no run data" if data is None else "supplied CSV plus separate illustrations"), fontsize=11)
            ax.text(.05, .67, "The parametric examples do not simulate fields, transport or hardware.\n"
                    "The CSV scatter reports supplied values; metric direction and units need source review.\n"
                    "No engineering superiority, energy saving or independent validation is established.\n"
                    "Exact inputs, source hashes and file hashes accompany this PDF in manifest.json.",
                    fontsize=11, linespacing=1.8)
            pdf.savefig(fig)
            plt.close(fig)
        inputs = {"source.py": snapshot(__file__), "artifact_io.py": snapshot(Path(__file__).with_name("research_artifact_io.py"))}
        if raw is not None:
            inputs["geometry.csv"] = raw
        return write_manifest(stage, {"tool": Path(__file__).name,
            "evidence_type": "illustrative geometry" if data is None else "unverified supplied geometry data plus illustrations",
            "supplied_rows": 0 if data is None else len(data["score"]), "notes": [BOUNDARY]}, inputs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--csv", type=Path)
    mode.add_argument("--illustrations-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    build_report(args.output, csv_path=args.csv, illustrations_only=args.illustrations_only)
    print(f"Descriptive geometry report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
