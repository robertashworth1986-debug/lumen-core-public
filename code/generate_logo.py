"""Generate LumenCore logo PNG (512x512 + 100x100) — violet harmonic-wave glyph + wordmark."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

OUT = Path(__file__).resolve().parent.parent / "dashboard" / "brand"
OUT.mkdir(parents=True, exist_ok=True)


def render(size_px: int, with_wordmark: bool, fname: str):
    dpi = 100
    inch = size_px / dpi
    fig, ax = plt.subplots(figsize=(inch, inch), dpi=dpi)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")

    # Outer ring
    ring = Circle((0.5, 0.5), 0.46, fill=False, lw=size_px * 0.012,
                  edgecolor="#7c3aed", alpha=0.9)
    ax.add_patch(ring)
    inner = Circle((0.5, 0.5), 0.42, fill=False, lw=size_px * 0.005,
                   edgecolor="#a855f7", alpha=0.4)
    ax.add_patch(inner)

    # Three superimposed harmonic waves (the routing thesis: multi-period harmonic)
    x = np.linspace(0.12, 0.88, 600)
    cx = 0.5 - (0.12 + 0.88) / 2 + 0.5  # centered
    waves = [
        (1.0,  0.07, 0.0,            "#a855f7", 1.0),
        (2.0,  0.05, np.pi / 3,      "#22d3ee", 0.85),
        (3.0,  0.035, np.pi / 1.5,   "#f0abfc", 0.7),
    ]
    for k, amp, phase, color, alpha in waves:
        y = 0.5 + amp * np.sin(2 * np.pi * k * (x - 0.12) / 0.76 + phase)
        ax.plot(x, y, color=color, lw=size_px * 0.009, alpha=alpha,
                solid_capstyle="round")

    # Center node
    ax.add_patch(Circle((0.5, 0.5), 0.035, color="#ffffff", zorder=5))
    ax.add_patch(Circle((0.5, 0.5), 0.018, color="#7c3aed", zorder=6))

    if with_wordmark:
        ax.text(0.5, 0.085, "L U M E N C O R E",
                ha="center", va="center", color="#e9e9ff",
                fontsize=size_px * 0.038, fontweight="bold",
                family="DejaVu Sans")

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    out = OUT / fname
    fig.savefig(out, dpi=dpi, facecolor="#0b1020")
    plt.close(fig)
    print(f"  wrote {out}  ({size_px}x{size_px})")


if __name__ == "__main__":
    render(512, with_wordmark=True,  fname="lumencore_logo_512.png")
    render(300, with_wordmark=True,  fname="lumencore_logo_300.png")
    render(200, with_wordmark=False, fname="lumencore_glyph_200.png")
    render(100, with_wordmark=False, fname="lumencore_glyph_100.png")
    print(f"\nAll logos -> {OUT}")
