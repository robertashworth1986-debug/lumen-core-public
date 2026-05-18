from __future__ import annotations

import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "linkedin_oauth_setup"


def _radial_background(size: int) -> Image.Image:
    np.random.seed(19)
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = size / 2.0

    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (size / 2.0)
    r = np.clip(r, 0.0, 1.0)

    inner = np.array([10.0, 34.0, 66.0], dtype=np.float32)
    outer = np.array([3.0, 12.0, 24.0], dtype=np.float32)
    bg = outer + (inner - outer) * ((1.0 - r) ** 1.45)[..., None]

    # Clean fintech texture: subtle grain + restrained vertical scan pattern.
    noise = np.random.normal(0.0, 1.5, (size, size, 1)).astype(np.float32)
    bg += noise

    scan = ((xx % 28) == 0).astype(np.float32)
    bg[..., 1] += scan * 1.2
    bg[..., 2] += scan * 2.0

    # Top-left directional light for premium depth.
    lx = size * 0.28
    ly = size * 0.22
    lr = np.sqrt((xx - lx) ** 2 + (yy - ly) ** 2) / (size * 0.82)
    lm = np.clip(1.0 - lr, 0.0, 1.0)
    bg[..., 0] += lm * 3.0
    bg[..., 1] += lm * 8.0
    bg[..., 2] += lm * 13.0

    vignette = np.clip(1.0 - (r ** 2.25), 0.0, 1.0)
    bg *= (0.78 + 0.22 * vignette)[..., None]

    out = np.clip(bg, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(out, mode="RGB").convert("RGBA")


def _quad_point(p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], t: float) -> tuple[float, float]:
    omt = 1.0 - t
    x = omt * omt * p0[0] + 2.0 * omt * t * p1[0] + t * t * p2[0]
    y = omt * omt * p0[1] + 2.0 * omt * t * p1[1] + t * t * p2[1]
    return x, y


def _cubic_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    omt = 1.0 - t
    x = (
        (omt * omt * omt) * p0[0]
        + (3.0 * omt * omt * t) * p1[0]
        + (3.0 * omt * t * t) * p2[0]
        + (t * t * t) * p3[0]
    )
    y = (
        (omt * omt * omt) * p0[1]
        + (3.0 * omt * omt * t) * p1[1]
        + (3.0 * omt * t * t) * p2[1]
        + (t * t * t) * p3[1]
    )
    return x, y


def _draw_variable_stroke(
    draw: ImageDraw.ImageDraw,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    w0: float,
    w1: float,
    steps: int,
) -> None:
    for i in range(steps + 1):
        t = i / float(steps)
        x, y = _quad_point(p0, p1, p2, t)
        w = w0 + (w1 - w0) * t
        r = max(1.0, w / 2.0)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=255)


def _draw_variable_stroke_cubic(
    draw: ImageDraw.ImageDraw,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    w0: float,
    w1: float,
    steps: int,
) -> None:
    for i in range(steps + 1):
        t = i / float(steps)
        x, y = _cubic_point(p0, p1, p2, p3, t)
        w = w0 + (w1 - w0) * t
        r = max(0.8, w / 2.0)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=255)


def _sample_cubic_points(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int,
    include_start: bool,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    start_i = 0 if include_start else 1
    for i in range(start_i, steps + 1):
        t = i / float(steps)
        points.append(_cubic_point(p0, p1, p2, p3, t))
    return points


def _catmull_rom_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    t2 = t * t
    t3 = t2 * t
    x = 0.5 * (
        (2.0 * p1[0])
        + (-p0[0] + p2[0]) * t
        + (2.0 * p0[0] - 5.0 * p1[0] + 4.0 * p2[0] - p3[0]) * t2
        + (-p0[0] + 3.0 * p1[0] - 3.0 * p2[0] + p3[0]) * t3
    )
    y = 0.5 * (
        (2.0 * p1[1])
        + (-p0[1] + p2[1]) * t
        + (2.0 * p0[1] - 5.0 * p1[1] + 4.0 * p2[1] - p3[1]) * t2
        + (-p0[1] + 3.0 * p1[1] - 3.0 * p2[1] + p3[1]) * t3
    )
    return x, y


def _sample_catmull_rom_points(
    control_points: list[tuple[float, float]],
    steps_per_segment: int,
) -> list[tuple[float, float]]:
    if len(control_points) < 2:
        return control_points

    pts: list[tuple[float, float]] = [control_points[0], *control_points, control_points[-1]]
    out: list[tuple[float, float]] = []

    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        start_j = 0 if i == 1 else 1
        for j in range(start_j, steps_per_segment + 1):
            t = j / float(steps_per_segment)
            out.append(_catmull_rom_point(p0, p1, p2, p3, t))

    return out


def _build_cursive_l_mask(size: int) -> Image.Image:
    # Supersample for cleaner anti-aliased edges at export sizes.
    aa = 2
    work_size = size * aa
    mask_hi = Image.new("L", (work_size, work_size), 0)
    draw = ImageDraw.Draw(mask_hi)

    s = float(work_size)

    # Hard geometric L with rounded engineering corners.
    stem_left = 0.366 * s
    stem_top = 0.246 * s
    stem_right = 0.474 * s
    stem_bottom = 0.788 * s

    foot_left = stem_left
    foot_top = 0.680 * s
    foot_right = 0.760 * s
    foot_bottom = stem_bottom

    radius = int(0.022 * s)
    draw.rounded_rectangle(
        (stem_left, stem_top, stem_right, stem_bottom),
        radius=radius,
        fill=255,
    )
    draw.rounded_rectangle(
        (foot_left, foot_top, foot_right, foot_bottom),
        radius=radius,
        fill=255,
    )

    # Subtle precision notch to avoid a blunt corner and add calculated character.
    notch = [
        (0.474 * s, 0.680 * s),
        (0.548 * s, 0.680 * s),
        (0.474 * s, 0.744 * s),
    ]
    draw.polygon(notch, fill=0)

    # Gentle smoothing while keeping edges crisp.
    mask_hi = mask_hi.filter(ImageFilter.GaussianBlur(max(1, work_size // 3600)))
    mask = mask_hi.resize((size, size), Image.Resampling.LANCZOS)

    # Trim ultra-faint fringe pixels so small logos stay clean.
    arr = np.array(mask, dtype=np.uint8)
    arr[arr < 18] = 0
    return Image.fromarray(arr, mode="L")


def _encode_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True, compress_level=9)
    return buf.getvalue()


def _save_png_under_max_bytes(
    image: Image.Image,
    out_path: Path,
    max_bytes: int,
    min_dim: int = 900,
) -> dict:
    source_w, source_h = image.size
    full_data = _encode_png_bytes(image)
    if len(full_data) <= max_bytes:
        out_path.write_bytes(full_data)
        return {
            "bytes": len(full_data),
            "size": [source_w, source_h],
        }

    lo = max(min_dim / float(source_w), min_dim / float(source_h))
    hi = 1.0
    best_data: bytes | None = None
    best_size = [source_w, source_h]

    for _ in range(16):
        mid = (lo + hi) / 2.0
        w = max(min_dim, int(source_w * mid))
        h = max(min_dim, int(source_h * mid))
        resized = image.resize((w, h), Image.Resampling.LANCZOS)
        data = _encode_png_bytes(resized)

        if len(data) <= max_bytes:
            best_data = data
            best_size = [w, h]
            lo = mid
        else:
            hi = mid

    if best_data is None:
        # Safety fallback if compression behavior is unusual.
        resized = image.resize((min_dim, min_dim), Image.Resampling.LANCZOS)
        best_data = _encode_png_bytes(resized)
        best_size = [min_dim, min_dim]

    out_path.write_bytes(best_data)
    return {
        "bytes": len(best_data),
        "size": best_size,
    }


def _compose_logo(size: int) -> Image.Image:
    base = _radial_background(size)
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = size / 2.0

    # Soft central disc to anchor the mark.
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (size * 0.43)
    core = np.clip(1.0 - rr, 0.0, 1.0)
    core_rgb = np.zeros((size, size, 3), dtype=np.float32)
    core_rgb[..., 0] = 18.0 + core * 10.0
    core_rgb[..., 1] = 58.0 + core * 40.0
    core_rgb[..., 2] = 104.0 + core * 70.0
    core_alpha = np.clip((core ** 1.8) * 120.0, 0.0, 255.0)
    core_layer = Image.fromarray(np.dstack([core_rgb, core_alpha]).astype(np.uint8), mode="RGBA")
    base.alpha_composite(core_layer)

    # Tetrahedron framing accents.
    tetra = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    td = ImageDraw.Draw(tetra)
    line_w = max(2, size // 235)
    inner_w = max(1, size // 300)

    a = (int(0.50 * size), int(0.145 * size))
    b = (int(0.246 * size), int(0.784 * size))
    c = (int(0.804 * size), int(0.744 * size))
    d = (int(0.558 * size), int(0.486 * size))

    # Front frame.
    td.line([a, b, c, a], fill=(90, 228, 255, 170), width=line_w)

    # Internal tetra edges.
    td.line([a, d], fill=(162, 244, 255, 134), width=inner_w)
    td.line([b, d], fill=(152, 236, 255, 116), width=inner_w)
    td.line([c, d], fill=(152, 236, 255, 116), width=inner_w)

    # Facet tints for subtle 3D read.
    td.polygon([a, b, d], fill=(18, 86, 126, 28))
    td.polygon([a, d, c], fill=(30, 104, 146, 24))
    td.polygon([b, d, c], fill=(16, 76, 114, 20))

    tetra_glow = tetra.filter(ImageFilter.GaussianBlur(max(1, size // 760)))
    base.alpha_composite(tetra_glow)
    base.alpha_composite(tetra)

    # Cursive L glyph.
    l_mask = _build_cursive_l_mask(size)

    glow_a = l_mask.filter(ImageFilter.GaussianBlur(max(1, size // 88)))
    glow_b = l_mask.filter(ImageFilter.GaussianBlur(max(1, size // 172)))
    glow_a_alpha = np.clip(np.array(glow_a, dtype=np.float32) * 0.30, 0.0, 255.0).astype(np.uint8)
    glow_b_alpha = np.clip(np.array(glow_b, dtype=np.float32) * 0.22, 0.0, 255.0).astype(np.uint8)

    glow_layer_a = Image.new("RGBA", (size, size), (44, 196, 255, 0))
    glow_layer_a.putalpha(Image.fromarray(glow_a_alpha, mode="L"))
    glow_layer_b = Image.new("RGBA", (size, size), (104, 235, 255, 0))
    glow_layer_b.putalpha(Image.fromarray(glow_b_alpha, mode="L"))
    base.alpha_composite(glow_layer_a)
    base.alpha_composite(glow_layer_b)

    y_norm = yy / float(size - 1)
    x_norm = xx / float(size - 1)

    top = np.array([248.0, 254.0, 255.0], dtype=np.float32)
    mid = np.array([166.0, 239.0, 255.0], dtype=np.float32)
    low = np.array([104.0, 222.0, 246.0], dtype=np.float32)

    grad = top + (mid - top) * np.clip(y_norm * 1.2, 0.0, 1.0)[..., None]
    grad = grad + (low - mid) * np.clip((y_norm - 0.33) / 0.67, 0.0, 1.0)[..., None]
    grad = grad + (np.array([8.0, 8.0, 8.0], dtype=np.float32) * np.clip((x_norm - 0.55) * 0.35, 0.0, 1.0)[..., None])

    alpha = np.array(l_mask, dtype=np.float32)
    glyph = Image.fromarray(np.dstack([grad, alpha]).astype(np.uint8), mode="RGBA")
    base.alpha_composite(glyph)

    # Crisp highlight edge.
    outer = l_mask.filter(ImageFilter.MaxFilter(3))
    edge = np.clip(np.array(outer, dtype=np.int16) - np.array(l_mask, dtype=np.int16), 0, 255).astype(np.uint8)
    edge_alpha = np.clip(edge.astype(np.float32) * 0.50, 0.0, 255.0).astype(np.uint8)
    edge_layer = Image.new("RGBA", (size, size), (232, 255, 255, 0))
    edge_layer.putalpha(Image.fromarray(edge_alpha, mode="L"))
    base.alpha_composite(edge_layer)

    # Specular pass on upper-left of block mark.
    sx = size * 0.43
    sy = size * 0.32
    sr = size * 0.18
    sr_map = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2) / sr
    spec = np.clip(1.0 - sr_map, 0.0, 1.0) ** 2.2
    spec *= np.array(l_mask, dtype=np.float32) / 255.0
    spec_alpha = np.clip(spec * 130.0, 0.0, 255.0).astype(np.uint8)
    spec_layer = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    spec_layer.putalpha(Image.fromarray(spec_alpha, mode="L"))
    spec_layer = spec_layer.filter(ImageFilter.GaussianBlur(max(1, size // 1000)))
    base.alpha_composite(spec_layer)

    return base


def generate_pack(master_size: int = 3072) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    logo = _compose_logo(master_size)

    out_3072 = OUT_DIR / "luma_logo_fintech_cursive_3072.png"
    out_2048 = OUT_DIR / "luma_logo_fintech_cursive_2048.png"
    out_1024 = OUT_DIR / "luma_logo_fintech_cursive_1024.png"
    out_512 = OUT_DIR / "luma_logo_fintech_cursive_512.png"
    out_5mb = OUT_DIR / "luma_logo_fintech_cursive_5mb.png"
    upload_alias = OUT_DIR / "luma_linkedin_logo_512.png"
    upload_alias_5mb = OUT_DIR / "luma_linkedin_logo_5mb.png"

    logo.save(out_3072, format="PNG", optimize=True, compress_level=9)
    logo.resize((2048, 2048), Image.Resampling.LANCZOS).save(out_2048, format="PNG", optimize=True, compress_level=9)
    logo.resize((1024, 1024), Image.Resampling.LANCZOS).save(out_1024, format="PNG", optimize=True, compress_level=9)
    logo.resize((512, 512), Image.Resampling.LANCZOS).save(out_512, format="PNG", optimize=True, compress_level=9)
    logo.resize((512, 512), Image.Resampling.LANCZOS).save(upload_alias, format="PNG", optimize=True, compress_level=9)

    five_mb_cap = 5_000_000
    five_mb_info = _save_png_under_max_bytes(logo, out_5mb, max_bytes=five_mb_cap)
    upload_alias_5mb.write_bytes(out_5mb.read_bytes())

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "fintech_cursive_logo_generation",
        "style": "luma_fintech_cursive_clean",
        "master_size": master_size,
        "outputs": {
            "logo_3072": str(out_3072),
            "logo_2048": str(out_2048),
            "logo_1024": str(out_1024),
            "logo_512": str(out_512),
            "linkedin_upload_alias": str(upload_alias),
            "logo_5mb_cap": str(out_5mb),
            "linkedin_upload_alias_5mb": str(upload_alias_5mb),
        },
        "size_control": {
            "max_bytes": five_mb_cap,
            "logo_5mb_cap_bytes": five_mb_info["bytes"],
            "logo_5mb_cap_dimensions": five_mb_info["size"],
        },
        "status": "ok",
    }

    summary_path = OUT_DIR / f"luma_logo_fintech_cursive_summary_{stamp}.json"
    latest_path = OUT_DIR / "luma_logo_fintech_cursive_summary_latest.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "summary_path": str(summary_path),
        "latest_path": str(latest_path),
        "logo_3072": str(out_3072),
        "logo_2048": str(out_2048),
        "logo_1024": str(out_1024),
        "logo_512": str(out_512),
        "logo_5mb_cap": str(out_5mb),
        "linkedin_upload_alias": str(upload_alias),
        "linkedin_upload_alias_5mb": str(upload_alias_5mb),
    }


if __name__ == "__main__":
    outputs = generate_pack(master_size=3072)
    for key, value in outputs.items():
        print(f"{key.upper()}={value}")
