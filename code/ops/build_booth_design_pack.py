from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "booth_design"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def banner_svg(title: str, subtitle: str, width_in: float = 96.0, height_in: float = 36.0) -> str:
    # 150 dpi print coordinates for easier vendor scaling.
    px_w = int(width_in * 150)
    px_h = int(height_in * 150)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{px_w}" height="{px_h}" viewBox="0 0 {px_w} {px_h}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#081221"/>
      <stop offset="50%" stop-color="#0d2f4f"/>
      <stop offset="100%" stop-color="#1e5b8f"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#06b6d4"/>
      <stop offset="100%" stop-color="#67e8f9"/>
    </linearGradient>
    <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="28" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <circle cx="{int(px_w*0.12)}" cy="{int(px_h*0.28)}" r="{int(px_h*0.25)}" fill="#0ea5e9" opacity="0.16" filter="url(#softGlow)"/>
  <circle cx="{int(px_w*0.88)}" cy="{int(px_h*0.72)}" r="{int(px_h*0.22)}" fill="#22d3ee" opacity="0.14" filter="url(#softGlow)"/>

  <g opacity="0.22" stroke="#8be9ff" stroke-width="4" fill="none">
    <path d="M 400 {int(px_h*0.78)} C {int(px_w*0.22)} {int(px_h*0.30)}, {int(px_w*0.44)} {int(px_h*0.22)}, {int(px_w*0.68)} {int(px_h*0.52)}"/>
    <path d="M {int(px_w*0.1)} {int(px_h*0.65)} C {int(px_w*0.30)} {int(px_h*0.35)}, {int(px_w*0.54)} {int(px_h*0.80)}, {int(px_w*0.9)} {int(px_h*0.38)}"/>
  </g>

  <rect x="{int(px_w*0.08)}" y="{int(px_h*0.19)}" width="{int(px_w*0.007)}" height="{int(px_h*0.62)}" rx="10" fill="url(#accent)"/>

  <text x="{int(px_w*0.13)}" y="{int(px_h*0.42)}" font-family="Montserrat, Arial, sans-serif" font-size="{int(px_h*0.19)}" font-weight="800" fill="#f3fbff" letter-spacing="7">{title}</text>
  <text x="{int(px_w*0.13)}" y="{int(px_h*0.58)}" font-family="Montserrat, Arial, sans-serif" font-size="{int(px_h*0.07)}" font-weight="600" fill="#c3ecff" letter-spacing="2">{subtitle}</text>
  <text x="{int(px_w*0.13)}" y="{int(px_h*0.71)}" font-family="Consolas, monospace" font-size="{int(px_h*0.045)}" fill="#86d9ff">INSTITUTIONAL • EVIDENCE-CHAINED • HARMONIC AI</text>
</svg>
"""


def logo_svg(brand: str, tag: str, size: int = 2200) -> str:
    s = size
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{s}" height="{s}" viewBox="0 0 {s} {s}">
  <defs>
    <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="100%" stop-color="#0ea5e9"/>
    </linearGradient>
    <linearGradient id="core" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0b1b32"/>
      <stop offset="100%" stop-color="#102a4a"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="none"/>
  <circle cx="{s//2}" cy="{s//2}" r="{int(s*0.40)}" fill="url(#core)"/>
  <circle cx="{s//2}" cy="{s//2}" r="{int(s*0.43)}" fill="none" stroke="url(#ring)" stroke-width="{int(s*0.03)}"/>
  <path d="M {int(s*0.22)} {int(s*0.52)} C {int(s*0.35)} {int(s*0.35)}, {int(s*0.58)} {int(s*0.70)}, {int(s*0.78)} {int(s*0.43)}" fill="none" stroke="#67e8f9" stroke-width="{int(s*0.02)}"/>
  <circle cx="{int(s*0.35)}" cy="{int(s*0.44)}" r="{int(s*0.018)}" fill="#67e8f9"/>
  <circle cx="{int(s*0.58)}" cy="{int(s*0.59)}" r="{int(s*0.018)}" fill="#67e8f9"/>
  <text x="50%" y="{int(s*0.83)}" text-anchor="middle" font-family="Montserrat, Arial, sans-serif" font-size="{int(s*0.09)}" font-weight="800" fill="#e6f6ff" letter-spacing="2">{brand}</text>
  <text x="50%" y="{int(s*0.90)}" text-anchor="middle" font-family="Montserrat, Arial, sans-serif" font-size="{int(s*0.038)}" fill="#9cdcff" letter-spacing="2">{tag}</text>
</svg>
"""


def print_spec_md() -> str:
    return """# Booth Design Print Spec

## Recommended Office Depot Output

1. Banner size: 96in x 36in (8ft x 3ft) horizontal.
2. Material: premium matte vinyl with anti-glare finish.
3. Color profile: CMYK conversion with proof print before full run.
4. Resolution target: 150 DPI at final print dimensions.
5. Bleed: 0.125in all sides.
6. Safe margin: keep critical text 1in from all edges.

## Files in this pack

- lumatrader_banner_8x3.svg
- lumaengine_banner_8x3.svg
- lumatrader_logo_lockup.svg
- lumaengine_logo_lockup.svg
- booth_design_manifest_latest.json

## Booth layout

1. Center back-wall: LumaTrader banner.
2. Left side panel: LumaEngine banner.
3. Podium/front desk: LumaTrader logo lockup.
4. Screen loop copy: use Luma Explainer quantified pack and booth explainer brief.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Office Depot-ready booth banner/logo design pack.")
    parser.add_argument("--width-in", type=float, default=96.0)
    parser.add_argument("--height-in", type=float, default=36.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = now_tag()

    files = {
        "lumatrader_banner_8x3.svg": banner_svg(
            "LUMATRADER",
            "Harmonic AI Execution • Institutional Evidence Stack",
            width_in=args.width_in,
            height_in=args.height_in,
        ),
        "lumaengine_banner_8x3.svg": banner_svg(
            "LUMAENGINE",
            "Flowform Intelligence • Sector-Scale Optimization",
            width_in=args.width_in,
            height_in=args.height_in,
        ),
        "lumatrader_logo_lockup.svg": logo_svg("LUMATRADER", "AUTONOMOUS QUANT EXECUTION"),
        "lumaengine_logo_lockup.svg": logo_svg("LUMAENGINE", "FLOWFORM OPTIMIZATION CORE"),
    }

    for name, content in files.items():
        write_text(OUT_DIR / name, content)

    spec = OUT_DIR / "booth_print_spec.md"
    write_text(spec, print_spec_md())

    manifest = {
        "generated_utc": now_iso(),
        "scope": "booth_design_pack_v1",
        "dimensions_in": {"width": args.width_in, "height": args.height_in},
        "files": {},
    }
    for path in sorted(OUT_DIR.glob("*.svg")) + [spec]:
        manifest["files"][str(path)] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }

    tagged_manifest = OUT_DIR / f"booth_design_manifest_{tag}.json"
    latest_manifest = OUT_DIR / "booth_design_manifest_latest.json"
    write_text(tagged_manifest, json.dumps(manifest, indent=2))
    write_text(latest_manifest, json.dumps(manifest, indent=2))

    print(f"OUT_DIR={OUT_DIR}")
    print(f"MANIFEST={tagged_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
