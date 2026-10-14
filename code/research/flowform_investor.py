"""Plot explicitly supplied HyperCore histories with truthful version labels."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from research_artifact_io import (
    BOUNDARY, columns, increasing, new_report, plotting, snapshot, strict_json, write_manifest,
)


def load_history(raw):
    rows = strict_json(raw)
    fields = ["step", "Omega", "S", "E"]
    if isinstance(rows, list) and any(isinstance(row, dict) and "C" in row for row in rows):
        fields.append("C")
    data = columns(rows, fields)
    increasing(data["step"])
    return data


def comparison_title(labels):
    if len(labels) == 1:
        return f"HyperCore Omega trajectory / {labels[0]} only (no version comparison)"
    return "HyperCore Omega trajectories / " + " vs ".join(labels)


def build_report(runs, output):
    if not runs or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", label) for label in runs):
        raise ValueError("provide runs with simple, distinct version labels")
    raw = {label: snapshot(path) for label, path in runs.items()}
    histories = {label: load_history(content) for label, content in raw.items()}
    plt = plotting()
    with new_report(output) as stage:
        for label, data in histories.items():
            fields = [key for key in ("C", "S", "E", "Omega") if key in data]
            fig, axes = plt.subplots(len(fields), 1, figsize=(10, 2.2 * len(fields)), sharex=True)
            for ax, key in zip(axes, fields):
                ax.plot(data["step"], data[key])
                ax.set_ylabel(f"{key} (source units)")
            axes[-1].set_xlabel("Step")
            fig.suptitle(f"{label} / recorded metrics; definitions require source verification")
            fig.tight_layout()
            fig.savefig(stage / f"{label}_timeseries.png", dpi=150)
            plt.close(fig)
            fig = plt.figure(figsize=(9, 6))
            ax = fig.add_subplot(111, projection="3d")
            ax.plot(data["step"], data["Omega"], data["E"])
            ax.set(xlabel="Step", ylabel="Omega (source units)", zlabel="E (source units)",
                   title=f"{label} / single-run trajectory, not a response surface")
            fig.tight_layout()
            fig.savefig(stage / f"{label}_trajectory.png", dpi=150)
            plt.close(fig)
        fig, ax = plt.subplots(figsize=(11, 5))
        for label, data in histories.items():
            ax.plot(data["step"], data["Omega"], label=label)
        title = comparison_title(list(histories))
        ax.set(title=title, xlabel="Step", ylabel="Omega (source units)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(stage / "Omega_Trajectories.png", dpi=150)
        plt.close(fig)
        return write_manifest(stage, {
            "tool": Path(__file__).name, "evidence_type": "unverified supplied numerical histories",
            "title": title, "versions_plotted": list(histories),
            "row_counts": {label: len(data["step"]) for label, data in histories.items()},
            "notes": [BOUNDARY, "No version superiority is inferred.",
                      "Matching units, metric direction, budgets, initial conditions and seeds remain unverified."],
        }, {**{f"{label}_history.json": content for label, content in raw.items()},
            "source.py": snapshot(__file__), "artifact_io.py": snapshot(Path(__file__).with_name("research_artifact_io.py"))})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, metavar="LABEL=HISTORY_JSON")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    runs = {}
    for item in args.run:
        label, separator, path = item.partition("=")
        if not separator or not path or label in runs:
            parser.error("each run requires a distinct LABEL=HISTORY_JSON")
        runs[label] = Path(path)
    build_report(runs, args.output)
    print(f"Descriptive charts written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
