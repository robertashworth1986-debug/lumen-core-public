from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "linkedin_oauth_setup"


def _radial_alpha(size: int, center: tuple[float, float], radius: float, power: float = 1.0) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size]
    cx, cy = center
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(radius, 1.0)
    mask = np.clip(1.0 - rr, 0.0, 1.0)
    if power != 1.0:
        mask = mask ** power
    return mask


def _poly_points(sides: int, radius: float, center: tuple[float, float], rotation_deg: float) -> list[tuple[float, float]]:
    cx, cy = center
    pts: list[tuple[float, float]] = []
    for i in range(sides):
        ang = math.radians(rotation_deg + i * (360.0 / sides))
        pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
    return pts


def _build_background(size: int) -> Image.Image:
    np.random.seed(42)
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = size / 2.0
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (size / 2.0)
    r = np.clip(r, 0.0, 1.0)

    inner = np.array([8.0, 33.0, 66.0], dtype=np.float32)
    outer = np.array([2.0, 9.0, 22.0], dtype=np.float32)
    bg = outer + (inner - outer) * ((1.0 - r) ** 1.45)[..., None]

    # Add subtle deterministic texture and a circuit-grid feel.
    noise = np.random.normal(0.0, 2.5, (size, size, 1)).astype(np.float32)
    bg += noise

    major_grid = ((xx % 128 == 0) | (yy % 128 == 0)).astype(np.float32)
    minor_grid = ((xx % 32 == 0) | (yy % 32 == 0)).astype(np.float32)
    diag_grid = (((xx + yy) % 96 == 0) | ((xx - yy) % 96 == 0)).astype(np.float32)

    bg[..., 0] += major_grid * 3.0 + minor_grid * 1.2 + diag_grid * 1.0
    bg[..., 1] += major_grid * 7.0 + minor_grid * 2.5 + diag_grid * 2.0
    bg[..., 2] += major_grid * 14.0 + minor_grid * 4.2 + diag_grid * 3.5

    # Add subtle directional glow for a cinematic depth pass.
    light_x = size * 0.35
    light_y = size * 0.23
    light_r = np.sqrt((xx - light_x) ** 2 + (yy - light_y) ** 2) / (size * 0.68)
    light = np.clip(1.0 - light_r, 0.0, 1.0)
    bg[..., 0] += light * 8.0
    bg[..., 1] += light * 18.0
    bg[..., 2] += light * 28.0

    vignette = np.clip(1.0 - (r ** 2.1), 0.0, 1.0)
    bg *= (0.72 + 0.28 * vignette)[..., None]

    # Micro scanline pattern for high-tech texture.
    scan = ((yy % 4) == 0).astype(np.float32)
    bg[..., 0] += scan * 0.55
    bg[..., 1] += scan * 1.0
    bg[..., 2] += scan * 1.45

    bg = np.clip(bg, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(bg, mode="RGB").convert("RGBA")


def _composite_neon_ring(base: Image.Image, radius: int, width: int, color: tuple[int, int, int], blur: int, alpha: int) -> None:
    size = base.size[0]
    cx = cy = size // 2
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.ellipse(bbox, outline=(color[0], color[1], color[2], alpha), width=width)
    if blur > 0:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)


def _composite_energy_arcs(base: Image.Image) -> None:
    size = base.size[0]
    arc_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(arc_layer)

    color_main = (62, 226, 255, 105)
    color_sub = (31, 139, 255, 75)
    widths = [max(2, size // 560), max(2, size // 700), max(1, size // 900)]

    for idx, frac in enumerate([0.43, 0.37, 0.315]):
        r = int(size * frac)
        bbox = [size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r]
        draw.arc(bbox, start=16, end=125, fill=color_main, width=widths[min(idx, len(widths) - 1)])
        draw.arc(bbox, start=196, end=292, fill=color_sub, width=widths[min(idx, len(widths) - 1)])

    arc_layer = arc_layer.filter(ImageFilter.GaussianBlur(max(1, size // 900)))
    base.alpha_composite(arc_layer)


def _composite_center_core(base: Image.Image, radius: int) -> None:
    size = base.size[0]
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = size / 2.0

    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / float(radius)
    mask = np.clip(1.0 - r, 0.0, 1.0)

    c0 = np.array([22.0, 96.0, 170.0], dtype=np.float32)
    c1 = np.array([78.0, 238.0, 255.0], dtype=np.float32)
    rgb = c0 + (c1 - c0) * (mask ** 0.65)[..., None]

    alpha = np.clip((mask ** 1.35) * 255.0, 0.0, 255.0)
    arr = np.dstack([rgb, alpha]).astype(np.uint8)
    layer = Image.fromarray(arr, mode="RGBA")
    layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    base.alpha_composite(layer)

    # Glass highlight pass.
    hr = radius * 0.58
    hx = cx - radius * 0.33
    hy = cy - radius * 0.42
    hr_map = np.sqrt((xx - hx) ** 2 + (yy - hy) ** 2) / float(hr)
    hmask = np.clip(1.0 - hr_map, 0.0, 1.0)
    h_alpha = (hmask ** 1.9) * 140.0
    h_rgb = np.zeros((size, size, 3), dtype=np.float32) + np.array([255.0, 255.0, 255.0], dtype=np.float32)
    h_arr = np.dstack([h_rgb, h_alpha]).astype(np.uint8)
    hlayer = Image.fromarray(h_arr, mode="RGBA").filter(ImageFilter.GaussianBlur(6))
    base.alpha_composite(hlayer)

    # Add a second softer volumetric bloom around the core.
    bloom_mask = _radial_alpha(size, (cx, cy), radius * 1.9, power=2.1)
    bloom_rgb = np.zeros((size, size, 3), dtype=np.float32)
    bloom_rgb[..., 0] = 36.0
    bloom_rgb[..., 1] = 172.0
    bloom_rgb[..., 2] = 255.0
    bloom_alpha = np.clip(bloom_mask * 95.0, 0.0, 255.0)
    bloom_arr = np.dstack([bloom_rgb, bloom_alpha]).astype(np.uint8)
    bloom = Image.fromarray(bloom_arr, mode="RGBA").filter(ImageFilter.GaussianBlur(max(2, size // 360)))
    base.alpha_composite(bloom)


def _make_monogram_mask(size: int) -> Image.Image:
    mono_mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mono_mask)

    s = float(size)
    x0, y0 = int(0.33 * s), int(0.25 * s)
    x1, y1 = int(0.51 * s), int(0.74 * s)

    draw.rounded_rectangle([x0, y0, x1, y1], radius=int(0.018 * s), fill=255)
    draw.rounded_rectangle([x0, int(0.62 * s), int(0.70 * s), int(0.74 * s)], radius=int(0.018 * s), fill=255)

    cut = ImageDraw.Draw(mono_mask)
    cut.polygon(
        [
            (int(0.51 * s), int(0.58 * s)),
            (int(0.63 * s), int(0.58 * s)),
            (int(0.70 * s), int(0.66 * s)),
            (int(0.58 * s), int(0.66 * s)),
        ],
        fill=0,
    )
    cut.rectangle([int(0.39 * s), int(0.41 * s), int(0.45 * s), int(0.44 * s)], fill=0)
    return mono_mask


def _composite_monogram(base: Image.Image) -> None:
    size = base.size[0]
    mono_mask = _make_monogram_mask(size)

    mask_arr = np.array(mono_mask, dtype=np.float32) / 255.0
    yy, xx = np.mgrid[0:size, 0:size]
    y_norm = yy / float(size - 1)
    x_norm = xx / float(size - 1)

    top = np.array([246.0, 253.0, 255.0], dtype=np.float32)
    bot = np.array([119.0, 229.0, 255.0], dtype=np.float32)
    edge = np.array([180.0, 244.0, 255.0], dtype=np.float32)
    grad = top + (bot - top) * y_norm[..., None]
    grad = grad + (edge - grad) * np.clip((1.0 - x_norm) * 0.22, 0.0, 1.0)[..., None]

    rgb = grad
    alpha = (mask_arr * 255.0)
    mono_arr = np.dstack([rgb, alpha]).astype(np.uint8)
    mono_layer = Image.fromarray(mono_arr, mode="RGBA")

    # Cyan glow behind the monogram for premium contrast.
    glow = mono_mask.filter(ImageFilter.GaussianBlur(28))
    glow_layer = Image.new("RGBA", (size, size), (68, 232, 255, 0))
    glow_layer.putalpha(glow)

    # Edge stroke and a hard specular highlight for more premium contrast.
    soft_mask = mono_mask.filter(ImageFilter.GaussianBlur(max(1, size // 820)))
    edge_arr = np.clip(
        np.array(mono_mask, dtype=np.int16) - np.array(soft_mask, dtype=np.int16),
        0,
        255,
    ).astype(np.uint8)
    edge_layer = Image.new("RGBA", (size, size), (196, 250, 255, 0))
    edge_layer.putalpha(Image.fromarray(edge_arr, mode="L"))

    spec_mask = _radial_alpha(size, (size * 0.44, size * 0.30), size * 0.18, power=2.0) * mask_arr
    spec_alpha = np.clip(spec_mask * 210.0, 0.0, 255.0)
    spec_arr = np.dstack([
        np.full((size, size), 255.0),
        np.full((size, size), 255.0),
        np.full((size, size), 255.0),
        spec_alpha,
    ]).astype(np.uint8)
    spec_layer = Image.fromarray(spec_arr, mode="RGBA").filter(ImageFilter.GaussianBlur(max(1, size // 700)))

    base.alpha_composite(glow_layer)
    base.alpha_composite(edge_layer)
    base.alpha_composite(mono_layer)
    base.alpha_composite(spec_layer)


def _render_scene(size: int, include_background: bool) -> Image.Image:
    if include_background:
        canvas = _build_background(size)
    else:
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    cx = cy = size // 2
    ring_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring_layer)

    for radius, alpha in [(int(size * 0.43), 102), (int(size * 0.355), 82), (int(size * 0.285), 60)]:
        pts = _poly_points(6, radius, (cx, cy), -30)
        d.polygon(pts, outline=(44, 193, 255, alpha), width=max(2, size // 420))

    ring_layer = ring_layer.filter(ImageFilter.GaussianBlur(max(1, size // 280)))
    canvas.alpha_composite(ring_layer)

    _composite_neon_ring(canvas, int(size * 0.395), max(3, size // 240), (34, 210, 255), max(1, size // 300), 180)
    _composite_neon_ring(canvas, int(size * 0.335), max(2, size // 320), (0, 138, 255), max(1, size // 360), 170)
    _composite_neon_ring(canvas, int(size * 0.258), max(2, size // 360), (89, 231, 255), max(1, size // 450), 170)

    _composite_energy_arcs(canvas)
    _composite_center_core(canvas, int(size * 0.245))
    _composite_monogram(canvas)

    accent = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ad = ImageDraw.Draw(accent)
    ad.line(
        [(int(size * 0.28), int(size * 0.52)), (int(size * 0.72), int(size * 0.52))],
        fill=(69, 227, 255, 70),
        width=max(1, size // 700),
    )
    ad.line(
        [(int(size * 0.50), int(size * 0.28)), (int(size * 0.50), int(size * 0.72))],
        fill=(69, 227, 255, 70),
        width=max(1, size // 700),
    )
    accent = accent.filter(ImageFilter.GaussianBlur(max(1, size // 600)))
    canvas.alpha_composite(accent)
    return canvas


def _render_linkedin_cover(scene: Image.Image, width: int = 1584, height: int = 396) -> Image.Image:
    bg = _build_background(max(width, height)).resize((width, height), Image.Resampling.LANCZOS)
    logo = scene.resize((height, height), Image.Resampling.LANCZOS)

    # Add left-weighted composition so profile avatar does not hide the mark.
    out = bg.copy()
    x = int(width * 0.08)
    y = int((height - logo.height) / 2)
    out.alpha_composite(logo, (x, y))

    haze = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(haze)
    draw.rectangle([0, 0, int(width * 0.7), height], fill=(9, 36, 72, 46))
    haze = haze.filter(ImageFilter.GaussianBlur(18))
    out.alpha_composite(haze)
    return out


def generate_logo_set(size: int = 2048) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    render_size = max(size, 3072)
    base = _render_scene(render_size, include_background=True)
    emblem = _render_scene(render_size, include_background=False)

    out_4096 = OUT_DIR / "luma_logo_ultra_4096.png"
    out_2048 = OUT_DIR / "luma_logo_topshelf_2048.png"
    out_1024 = OUT_DIR / "luma_logo_topshelf_1024.png"
    out_512 = OUT_DIR / "luma_logo_topshelf_512.png"
    out_emblem_transparent = OUT_DIR / "luma_emblem_transparent_2048.png"
    out_cover_1584 = OUT_DIR / "luma_linkedin_cover_1584x396.png"
    out_cover_1128 = OUT_DIR / "luma_linkedin_cover_1128x191.png"
    upload_alias = OUT_DIR / "luma_linkedin_logo_512.png"

    base.save(out_4096, format="PNG", optimize=True)
    base.save(out_2048, format="PNG", optimize=True)
    base.resize((1024, 1024), Image.Resampling.LANCZOS).save(out_1024, format="PNG", optimize=True)
    base.resize((512, 512), Image.Resampling.LANCZOS).save(out_512, format="PNG", optimize=True)
    base.resize((512, 512), Image.Resampling.LANCZOS).save(upload_alias, format="PNG", optimize=True)

    emblem.resize((2048, 2048), Image.Resampling.LANCZOS).save(out_emblem_transparent, format="PNG", optimize=True)

    cover_large = _render_linkedin_cover(base, width=1584, height=396)
    cover_small = _render_linkedin_cover(base, width=1128, height=191)
    cover_large.save(out_cover_1584, format="PNG", optimize=True)
    cover_small.save(out_cover_1128, format="PNG", optimize=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "premium_logo_generation",
        "style": "luma_ultra_topshelf_tech",
        "render_size": render_size,
        "outputs": {
            "logo_4096": str(out_4096),
            "logo_2048": str(out_2048),
            "logo_1024": str(out_1024),
            "logo_512": str(out_512),
            "emblem_transparent_2048": str(out_emblem_transparent),
            "linkedin_cover_1584x396": str(out_cover_1584),
            "linkedin_cover_1128x191": str(out_cover_1128),
            "linkedin_upload_alias": str(upload_alias),
        },
        "status": "ok",
    }

    summary_path = OUT_DIR / f"luma_logo_topshelf_summary_{stamp}.json"
    latest_path = OUT_DIR / "luma_logo_topshelf_summary_latest.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "summary_path": str(summary_path),
        "latest_path": str(latest_path),
        "logo_4096": str(out_4096),
        "logo_2048": str(out_2048),
        "logo_1024": str(out_1024),
        "logo_512": str(out_512),
        "emblem_transparent_2048": str(out_emblem_transparent),
        "linkedin_cover_1584x396": str(out_cover_1584),
        "linkedin_cover_1128x191": str(out_cover_1128),
        "linkedin_upload_alias": str(upload_alias),
    }


if __name__ == "__main__":
    outputs = generate_logo_set(size=2048)
    for k, v in outputs.items():
        print(f"{k.upper()}={v}")
