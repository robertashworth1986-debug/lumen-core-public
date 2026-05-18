from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "linkedin_oauth_setup"


def _pick_cursive_font(px_size: int) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, str]:
    candidates = [
        Path("C:/Windows/Fonts/segoesc.ttf"),
        Path("C:/Windows/Fonts/BRUSHSCI.TTF"),
        Path("C:/Windows/Fonts/seguisbi.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), px_size), str(candidate)
            except Exception:
                continue
    return ImageFont.load_default(), "PIL_default"


def _build_background(size: int) -> Image.Image:
    np.random.seed(11)
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = size / 2.0

    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (size / 2.0)
    r = np.clip(r, 0.0, 1.0)

    inner = np.array([8.0, 36.0, 70.0], dtype=np.float32)
    outer = np.array([2.0, 8.0, 20.0], dtype=np.float32)
    bg = outer + (inner - outer) * ((1.0 - r) ** 1.5)[..., None]

    # Subtle directional light for polish.
    lx = size * 0.30
    ly = size * 0.22
    lr = np.sqrt((xx - lx) ** 2 + (yy - ly) ** 2) / (size * 0.75)
    lm = np.clip(1.0 - lr, 0.0, 1.0)
    bg[..., 0] += lm * 6.0
    bg[..., 1] += lm * 14.0
    bg[..., 2] += lm * 24.0

    # Fine texture for anti-flat look.
    grain = np.random.normal(0.0, 2.1, (size, size, 1)).astype(np.float32)
    bg += grain

    grid = ((xx % 48 == 0) | (yy % 48 == 0)).astype(np.float32)
    bg[..., 1] += grid * 1.2
    bg[..., 2] += grid * 2.0

    vignette = np.clip(1.0 - (r ** 2.2), 0.0, 1.0)
    bg *= (0.74 + 0.26 * vignette)[..., None]

    arr = np.clip(bg, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB").convert("RGBA")


def _draw_cursive_l_mark(canvas: Image.Image) -> dict:
    size = canvas.size[0]
    font, font_name = _pick_cursive_font(int(size * 0.62))
    text = "L"

    probe = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Offset tuned for script overhang and LinkedIn readability.
    x = int((size - tw) / 2 - size * 0.02 - bbox[0])
    y = int((size - th) / 2 - size * 0.12 - bbox[1])

    # Neon halo passes.
    for blur, alpha in [(size // 24, 96), (size // 44, 132), (size // 80, 166)]:
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.text((x, y), text, font=font, fill=(64, 218, 255, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(max(1, blur)))
        canvas.alpha_composite(glow)

    # Build gradient-filled script glyph.
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.text((x, y), text, font=font, fill=255)

    mask_arr = np.array(mask, dtype=np.float32) / 255.0
    yy, xx = np.mgrid[0:size, 0:size]
    y_norm = yy / float(size - 1)

    top = np.array([245.0, 252.0, 255.0], dtype=np.float32)
    mid = np.array([175.0, 241.0, 255.0], dtype=np.float32)
    bot = np.array([116.0, 224.0, 255.0], dtype=np.float32)

    grad = top + (mid - top) * np.clip(y_norm * 1.3, 0.0, 1.0)[..., None]
    grad = grad + (bot - mid) * np.clip((y_norm - 0.35) / 0.65, 0.0, 1.0)[..., None]

    alpha = np.clip(mask_arr * 255.0, 0.0, 255.0)
    glyph = np.dstack([grad, alpha]).astype(np.uint8)
    glyph_layer = Image.fromarray(glyph, mode="RGBA")
    canvas.alpha_composite(glyph_layer)

    # Specular highlight.
    sx = size * 0.43
    sy = size * 0.28
    sr = size * 0.20
    rr = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2) / max(sr, 1.0)
    sm = np.clip(1.0 - rr, 0.0, 1.0) ** 2.0
    sm *= mask_arr

    s_alpha = np.clip(sm * 205.0, 0.0, 255.0)
    sl = np.dstack([
        np.full((size, size), 255, dtype=np.uint8),
        np.full((size, size), 255, dtype=np.uint8),
        np.full((size, size), 255, dtype=np.uint8),
        s_alpha.astype(np.uint8),
    ])
    spec_layer = Image.fromarray(sl, mode="RGBA").filter(ImageFilter.GaussianBlur(max(1, size // 700)))
    canvas.alpha_composite(spec_layer)

    # A restrained ring keeps the tech signal while preserving readability.
    ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    r = int(size * 0.39)
    rd.ellipse([size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r], outline=(36, 188, 255, 72), width=max(2, size // 190))
    ring = ring.filter(ImageFilter.GaussianBlur(max(1, size // 520)))
    canvas.alpha_composite(ring)

    return {
        "font": font_name,
        "glyph_anchor": {"x": x, "y": y},
    }


def generate_cursive_logo_pack(master_size: int = 3072) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base = _build_background(master_size)
    info = _draw_cursive_l_mark(base)

    out_3072 = OUT_DIR / "luma_logo_cursive_3072.png"
    out_2048 = OUT_DIR / "luma_logo_cursive_2048.png"
    out_1024 = OUT_DIR / "luma_logo_cursive_1024.png"
    out_512 = OUT_DIR / "luma_logo_cursive_512.png"
    upload_alias = OUT_DIR / "luma_linkedin_logo_512.png"

    base.save(out_3072, format="PNG", optimize=True)
    base.resize((2048, 2048), Image.Resampling.LANCZOS).save(out_2048, format="PNG", optimize=True)
    base.resize((1024, 1024), Image.Resampling.LANCZOS).save(out_1024, format="PNG", optimize=True)
    base.resize((512, 512), Image.Resampling.LANCZOS).save(out_512, format="PNG", optimize=True)
    base.resize((512, 512), Image.Resampling.LANCZOS).save(upload_alias, format="PNG", optimize=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "cursive_logo_generation",
        "style": "luma_cursive_premium",
        "master_size": master_size,
        "font_used": info["font"],
        "outputs": {
            "logo_3072": str(out_3072),
            "logo_2048": str(out_2048),
            "logo_1024": str(out_1024),
            "logo_512": str(out_512),
            "linkedin_upload_alias": str(upload_alias),
        },
        "status": "ok",
    }

    summary_path = OUT_DIR / f"luma_logo_cursive_summary_{stamp}.json"
    latest_path = OUT_DIR / "luma_logo_cursive_summary_latest.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "summary_path": str(summary_path),
        "latest_path": str(latest_path),
        "logo_3072": str(out_3072),
        "logo_2048": str(out_2048),
        "logo_1024": str(out_1024),
        "logo_512": str(out_512),
        "linkedin_upload_alias": str(upload_alias),
    }


if __name__ == "__main__":
    outputs = generate_cursive_logo_pack(master_size=3072)
    for k, v in outputs.items():
        print(f"{k.upper()}={v}")
