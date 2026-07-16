from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "evidence" / "external_validation" / "frequency_cluster_reviewer_decision_20260716.json"
DEFAULT_OUT = ROOT / "out" / "social" / "tiktok_truth_over_hype_v1_20260716"

ASSETS = {
    "founder_laptop": Path(r"C:\Users\Novac\Downloads\IMG_6468 (1).jpeg"),
    "github_failure": Path(r"C:\Users\Novac\Pictures\iCloud Photos\Photos\IMG_6794.PNG"),
    "mission_control": ROOT / "output" / "playwright" / "mission_control_reviewer_1440.png",
    "grants_reviewer": ROOT / "output" / "playwright" / "grants-reviewer-desktop-final.png",
}

WIDTH = 1080
HEIGHT = 1920
FPS = 30
MOTION_FPS = 15
DURATION = 32.0

BG = (7, 15, 26)
PANEL = (13, 29, 45)
PANEL_LIGHT = (21, 43, 61)
WHITE = (240, 247, 250)
MUTED = (151, 170, 181)
TEAL = (43, 210, 190)
CYAN = (47, 191, 230)
AMBER = (245, 179, 66)
RED = (242, 87, 87)
GREEN = (83, 209, 132)

FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_MONO = Path(r"C:\Windows\Fonts\consola.ttf")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    selected = FONT_MONO if mono else (FONT_BOLD if bold else FONT_REGULAR)
    return ImageFont.truetype(str(selected), size=size)


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def scene_progress(t: float, start: float, end: float) -> float:
    return ease((t - start) / max(0.001, end - start))


def fade_for_scene(t: float, start: float, end: float, edge: float = 0.35) -> float:
    return min(
        1.0,
        max(0.0, (t - start) / edge),
        max(0.0, (end - t) / edge),
    )


def alpha_color(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return (*color, int(max(0.0, min(1.0, alpha)) * 255))


def cover_crop(image: Image.Image, size: tuple[int, int], focus_y: float = 0.5) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize(
        (max(target_w, int(image.width * scale)), max(target_h, int(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (resized.width - target_w) // 2)
    max_top = max(0, resized.height - target_h)
    top = int(max_top * max(0.0, min(1.0, focus_y)))
    return resized.crop((left, top, left + target_w, top + target_h))


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paste_panel(
    frame: Image.Image,
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    radius: int = 26,
    focus_y: float = 0.5,
    dim: float = 0.0,
    blur: float = 0.0,
) -> None:
    x0, y0, x1, y1 = box
    panel = cover_crop(image, (x1 - x0, y1 - y0), focus_y=focus_y)
    if dim > 0:
        panel = ImageEnhance.Brightness(panel).enhance(max(0.0, 1.0 - dim))
    if blur > 0:
        panel = panel.filter(ImageFilter.GaussianBlur(blur))
    mask = rounded_mask(panel.size, radius)
    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x0 + 10, y0 + 18, x1 + 10, y1 + 18), radius=radius, fill=(0, 0, 0, 105)
    )
    frame.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(16)))
    frame.paste(panel.convert("RGBA"), (x0, y0), mask)
    ImageDraw.Draw(frame).rounded_rectangle(box, radius=radius, outline=TEAL, width=3)


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    max_width: int,
    selected_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    *,
    spacing: int = 10,
    anchor: str = "la",
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=selected_font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    draw.multiline_text(xy, "\n".join(lines), font=selected_font, fill=fill, spacing=spacing, anchor=anchor)
    line_height = selected_font.size + spacing
    return len(lines) * line_height


def draw_brand(draw: ImageDraw.ImageDraw, *, alpha: float = 1.0) -> None:
    a = int(255 * alpha)
    draw.ellipse((72, 70, 118, 116), outline=(*TEAL, a), width=4)
    draw.ellipse((84, 82, 106, 104), fill=(*CYAN, a))
    draw.text((136, 70), "LUMENCORE", font=font(31, bold=True), fill=(*WHITE, a))
    draw.text((136, 108), "MEASURE FIRST", font=font(18, mono=True), fill=(*MUTED, a))


def draw_base(t: float) -> Image.Image:
    frame = Image.new("RGBA", (WIDTH, HEIGHT), (*BG, 255))
    draw = ImageDraw.Draw(frame, "RGBA")
    for y in range(0, HEIGHT, 72):
        draw.line((0, y, WIDTH, y), fill=(31, 67, 81, 35), width=1)
    for x in range(0, WIDTH, 72):
        draw.line((x, 0, x, HEIGHT), fill=(31, 67, 81, 24), width=1)
    scan_y = int((t * 150) % (HEIGHT + 180)) - 90
    draw.rectangle((0, scan_y, WIDTH, scan_y + 4), fill=(43, 210, 190, 26))
    draw_brand(draw)
    draw.text((72, 1760), "Evidence, not investment advice", font=font(22), fill=MUTED)
    return frame


def draw_pill(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], color: tuple[int, int, int]) -> None:
    selected_font = font(23, bold=True)
    bbox = draw.textbbox((0, 0), text, font=selected_font)
    width = bbox[2] - bbox[0] + 36
    height = 52
    x, y = xy
    draw.rounded_rectangle((x, y, x + width, y + height), radius=12, fill=(*color, 38), outline=color, width=2)
    draw.text((x + 18, y + 12), text, font=selected_font, fill=WHITE)


def scene_hook(frame: Image.Image, t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    alpha = fade_for_scene(t, 0.0, 3.4)
    draw = ImageDraw.Draw(frame, "RGBA")
    pulse = 1.0 + 0.02 * math.sin(t * math.tau * 1.3)
    panel_w, panel_h = int(930 * pulse), int(930 * pulse)
    x0 = (WIDTH - panel_w) // 2
    paste_panel(
        frame,
        assets["mission_control"],
        (x0, 350, x0 + panel_w, 350 + panel_h),
        focus_y=0.05,
        dim=0.48,
        blur=5.0,
    )
    draw.rounded_rectangle((52, 245, 1028, 660), radius=30, fill=(4, 11, 19, 218))
    draw_wrapped(draw, "MY AI FOUND +1.45%", (82, 286), 900, font(67, bold=True), alpha_color(WHITE, alpha), spacing=8)
    draw_wrapped(draw, "THEN IT SAID:", (82, 420), 900, font(46, bold=True), alpha_color(MUTED, alpha))
    draw_wrapped(draw, "DON'T TRADE.", (82, 505), 900, font(78, bold=True), alpha_color(RED, alpha))
    draw_pill(draw, "THE INTERESTING PART IS WHY", (82, 1385), AMBER)


def scene_founder(frame: Image.Image, t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    alpha = fade_for_scene(t, 3.4, 7.2)
    progress = scene_progress(t, 3.4, 7.2)
    draw = ImageDraw.Draw(frame, "RGBA")
    focus = 0.48 + 0.08 * progress
    paste_panel(frame, assets["founder_laptop"], (66, 300, 1014, 1280), focus_y=focus, dim=0.12)
    draw.rounded_rectangle((52, 215, 1028, 535), radius=30, fill=(4, 11, 19, 224))
    draw_wrapped(draw, "MOST AI DEMOS ONLY SHOW THE WIN.", (82, 260), 900, font(60, bold=True), alpha_color(WHITE, alpha), spacing=8)
    draw.rounded_rectangle((70, 1320, 1010, 1615), radius=26, fill=(*PANEL, 244), outline=TEAL, width=2)
    draw_wrapped(
        draw,
        "We built the opposite: a system that can stop itself when the stronger test says no.",
        (105, 1370),
        870,
        font(41, bold=True),
        alpha_color(WHITE, alpha),
        spacing=12,
    )


def scene_two_results(frame: Image.Image, t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    alpha = fade_for_scene(t, 7.2, 11.4)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((72, 230), "ONE DATASET. TWO QUESTIONS.", font=font(43, bold=True), fill=alpha_color(WHITE, alpha))
    cards = [
        ("DIAGNOSTIC", f"+{metrics['diagnostic']:.6f}%", "vs one global baseline | diagnostic only", TEAL),
        ("REVIEWER GATE", f"{metrics['reviewer']:.6f}%", "vs strongest baseline per pair", RED),
    ]
    for idx, (label, value, note, color) in enumerate(cards):
        y0 = 380 + idx * 510
        draw.rounded_rectangle((70, y0, 1010, y0 + 430), radius=28, fill=(*PANEL, 247), outline=color, width=3)
        draw.text((110, y0 + 55), label, font=font(29, bold=True), fill=alpha_color(color, alpha))
        draw.text((110, y0 + 125), value, font=font(82, bold=True, mono=True), fill=alpha_color(WHITE, alpha))
        draw_wrapped(draw, note, (110, y0 + 255), 820, font(34), alpha_color(MUTED, alpha))
    draw_wrapped(draw, "The stricter question controls the decision.", (72, 1485), 900, font(44, bold=True), AMBER)


def scene_data(frame: Image.Image, t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    alpha = fade_for_scene(t, 11.4, 15.2)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((72, 230), "THE TEST WAS FROZEN FIRST", font=font(48, bold=True), fill=alpha_color(WHITE, alpha))
    items = [
        ("20", "fixed major pairs"),
        ("719", "daily returns per pair"),
        ("30%", "untouched holdout"),
        ("PUBLIC", "Kraken Spot REST source"),
    ]
    for idx, (value, label) in enumerate(items):
        col = idx % 2
        row = idx // 2
        x0 = 70 + col * 480
        y0 = 380 + row * 430
        draw.rounded_rectangle((x0, y0, x0 + 440, y0 + 350), radius=24, fill=(*PANEL, 247), outline=PANEL_LIGHT, width=2)
        draw.text((x0 + 35, y0 + 58), value, font=font(63, bold=True, mono=True), fill=alpha_color(TEAL, alpha))
        draw_wrapped(draw, label, (x0 + 35, y0 + 170), 360, font(35, bold=True), alpha_color(WHITE, alpha), spacing=8)
    draw_wrapped(draw, "Chronological splits. No holdout selection.", (72, 1345), 900, font(42, bold=True), AMBER)


def scene_pairs(frame: Image.Image, t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    alpha = fade_for_scene(t, 15.2, 19.1)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((72, 230), "THE GATE MISSED BY ONE PAIR", font=font(49, bold=True), fill=alpha_color(WHITE, alpha))
    positive = int(metrics["positive"])
    total = int(metrics["total"])
    required = int(math.ceil(float(metrics["required_fraction"]) * total))
    for index in range(total):
        row = index // 5
        col = index % 5
        cx = 145 + col * 175
        cy = 470 + row * 190
        color = TEAL if index < positive else (73, 92, 105)
        draw.ellipse((cx - 42, cy - 42, cx + 42, cy + 42), fill=alpha_color(color, alpha), outline=WHITE, width=2)
        draw.text((cx, cy), str(index + 1), font=font(23, bold=True), fill=BG, anchor="mm")
    draw.rounded_rectangle((70, 1320, 1010, 1610), radius=26, fill=(*PANEL, 247), outline=RED, width=3)
    draw.text((110, 1372), f"{positive}/{total} POSITIVE = {positive / total:.0%}", font=font(46, bold=True), fill=alpha_color(WHITE, alpha))
    draw.text((110, 1456), f"GATE REQUIRED {required}/{total} = {required / total:.0%}", font=font(38, bold=True), fill=alpha_color(RED, alpha))
    draw.text((110, 1530), "RESULT: REJECTED", font=font(34, bold=True, mono=True), fill=alpha_color(AMBER, alpha))


def scene_gauntlet(frame: Image.Image, t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    alpha = fade_for_scene(t, 19.1, 23.3)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((72, 230), "FIVE CHECKS. FIVE FAILS.", font=font(54, bold=True), fill=alpha_color(WHITE, alpha))
    checks = [
        "Aggregate effect positive",
        "Bootstrap lower bound positive",
        "Minimum positive-pair fraction",
        "Leave-one-pair-out positive",
        "Individually promoted pairs",
    ]
    for idx, label in enumerate(checks):
        y = 395 + idx * 205
        draw.rounded_rectangle((70, y, 1010, y + 155), radius=22, fill=(*PANEL, 247), outline=(82, 105, 120), width=2)
        draw.ellipse((105, y + 49, 165, y + 109), fill=RED)
        draw.line((122, y + 66, 148, y + 92), fill=WHITE, width=6)
        draw.line((148, y + 66, 122, y + 92), fill=WHITE, width=6)
        draw.text((205, y + 50), label, font=font(32, bold=True), fill=alpha_color(WHITE, alpha))
    draw.text((72, 1495), "0/20 PROMOTED", font=font(58, bold=True, mono=True), fill=alpha_color(RED, alpha))


def scene_integrity(frame: Image.Image, t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    alpha = fade_for_scene(t, 23.3, 27.2)
    draw = ImageDraw.Draw(frame, "RGBA")
    paste_panel(frame, assets["github_failure"], (420, 250, 1015, 1420), focus_y=0.1, dim=0.42)
    draw.rounded_rectangle((50, 230, 750, 1530), radius=30, fill=(4, 11, 19, 232))
    draw.text((82, 285), "FAILURE IS DATA", font=font(55, bold=True), fill=alpha_color(WHITE, alpha))
    statements = [
        ("DUPLICATE INPUT", "BLOCKED"),
        ("SOURCE SNAPSHOT", "HASHED"),
        ("EVIDENCE RECEIPTS", "CHAINED"),
        ("ECONOMIC ACTION", "DISABLED"),
    ]
    for idx, (label, value) in enumerate(statements):
        y = 465 + idx * 235
        draw.text((85, y), label, font=font(24, bold=True, mono=True), fill=alpha_color(MUTED, alpha))
        draw.text((85, y + 57), value, font=font(47, bold=True), fill=alpha_color(TEAL if idx < 3 else RED, alpha))
    draw_wrapped(draw, "A system earns trust by recording the stop.", (82, 1410), 610, font(37, bold=True), AMBER)


def scene_close(frame: Image.Image, t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    alpha = fade_for_scene(t, 27.2, 32.0, edge=0.5)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.rounded_rectangle((70, 270, 1010, 1380), radius=34, fill=(*PANEL, 248), outline=TEAL, width=3)
    draw.text((110, 350), "TRUTH OVER HYPE", font=font(66, bold=True), fill=alpha_color(WHITE, alpha))
    draw.text((110, 465), "28 TESTS PASSED", font=font(39, bold=True, mono=True), fill=alpha_color(GREEN, alpha))
    draw.text((110, 545), "BLIND KIT READY", font=font(39, bold=True, mono=True), fill=alpha_color(TEAL, alpha))
    draw.text((110, 625), "INDEPENDENT REVIEW: PENDING", font=font(31, bold=True, mono=True), fill=alpha_color(AMBER, alpha))
    draw.line((110, 735, 970, 735), fill=PANEL_LIGHT, width=3)
    draw_wrapped(
        draw,
        "Independent reviewers: run the kit. Try to break it. Return the receipt.",
        (110, 805),
        820,
        font(49, bold=True),
        alpha_color(WHITE, alpha),
        spacing=12,
    )
    draw.text((110, 1145), "lumen-core.ai", font=font(52, bold=True), fill=alpha_color(CYAN, alpha))
    draw.text((110, 1235), "LUMENCORE | MEASURE FIRST", font=font(27, bold=True, mono=True), fill=alpha_color(MUTED, alpha))
    draw.text((72, 1490), "No performance claim. No trade recommendation.", font=font(29, bold=True), fill=alpha_color(MUTED, alpha))


def render_frame(t: float, metrics: dict[str, object], assets: dict[str, Image.Image]) -> Image.Image:
    frame = draw_base(t)
    if t < 3.4:
        scene_hook(frame, t, metrics, assets)
    elif t < 7.2:
        scene_founder(frame, t, metrics, assets)
    elif t < 11.4:
        scene_two_results(frame, t, metrics, assets)
    elif t < 15.2:
        scene_data(frame, t, metrics, assets)
    elif t < 19.1:
        scene_pairs(frame, t, metrics, assets)
    elif t < 23.3:
        scene_gauntlet(frame, t, metrics, assets)
    elif t < 27.2:
        scene_integrity(frame, t, metrics, assets)
    else:
        scene_close(frame, t, metrics, assets)
    return frame.convert("RGB")


def load_and_validate_receipt() -> tuple[dict[str, object], dict[str, object]]:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    expected_decision = "NULL_OR_ADVERSE_NOT_PROMOTED_DO_NOT_RUN_ECONOMIC_ACTION"
    failures: list[str] = []
    if payload.get("decision") != expected_decision:
        failures.append("unexpected decision")
    if payload.get("execution_authorized") is not False:
        failures.append("execution must remain unauthorized")
    if payload.get("capital_at_risk_allowed") is not False:
        failures.append("capital at risk must remain disallowed")
    if payload.get("independently_validated") is not False:
        failures.append("independent validation must remain false")
    official = payload.get("official_source", {})
    if not isinstance(official, dict) or official.get("source_authentic") is not True:
        failures.append("source-authentic receipt missing")
    gate = payload.get("reviewer_grade_gate", {})
    if not isinstance(gate, dict) or gate.get("gate_pass") is not False:
        failures.append("reviewer gate must remain failed")
    if failures:
        raise RuntimeError("Claim-safety check failed: " + "; ".join(failures))
    diagnostic = payload["diagnostic_global_comparison"]
    metrics: dict[str, object] = {
        "diagnostic": float(diagnostic["improvement_pct_vs_one_global_strongest_named_baseline"]),
        "reviewer": float(gate["mean_pair_improvement_pct"]),
        "positive": int(gate["positive_pairs"]),
        "total": int(gate["total_pairs"]),
        "required_fraction": float(gate["required_positive_pair_fraction"]),
        "promoted": len(gate["individually_promoted_pairs"]),
        "decision": payload["decision"],
        "receipt_sha256": payload["integrity"]["primary_evidence_receipt_sha256"],
        "run_identity_sha256": payload["integrity"]["run_identity_sha256"],
    }
    return payload, metrics


def load_assets() -> dict[str, Image.Image]:
    missing = [str(path) for path in ASSETS.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing visual assets: " + ", ".join(missing))
    return {
        name: ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        for name, path in ASSETS.items()
    }


def build_audio(path: Path) -> None:
    sample_rate = 48_000
    count = int(DURATION * sample_rate)
    timeline = np.arange(count, dtype=np.float64) / sample_rate
    audio = np.zeros(count, dtype=np.float64)
    rng = np.random.default_rng(20260716)

    bpm = 100.0
    beat_seconds = 60.0 / bpm
    notes = [55.0, 65.406, 73.416, 49.0]
    for beat_index, start in enumerate(np.arange(0.0, DURATION, beat_seconds)):
        offset = int(start * sample_rate)
        length = min(int(0.38 * sample_rate), count - offset)
        local_t = np.arange(length) / sample_rate
        kick = np.sin(2 * math.pi * (54.0 * local_t + 42.0 * local_t * np.exp(-local_t * 20.0)))
        kick *= np.exp(-local_t * 12.0) * 0.24
        audio[offset : offset + length] += kick
        note = notes[beat_index % len(notes)]
        pad_length = min(int(beat_seconds * 1.8 * sample_rate), count - offset)
        pad_t = np.arange(pad_length) / sample_rate
        envelope = np.minimum(1.0, pad_t * 8.0) * np.exp(-pad_t * 1.35)
        pad = (
            np.sin(2 * math.pi * note * pad_t)
            + 0.42 * np.sin(2 * math.pi * note * 2.0 * pad_t)
            + 0.18 * np.sin(2 * math.pi * note * 3.0 * pad_t)
        )
        audio[offset : offset + pad_length] += pad * envelope * 0.055

    for start in (3.4, 7.2, 11.4, 15.2, 19.1, 23.3, 27.2):
        offset = int(start * sample_rate)
        length = min(int(0.42 * sample_rate), count - offset)
        local_t = np.arange(length) / sample_rate
        click = rng.normal(0.0, 1.0, length) * np.exp(-local_t * 18.0) * 0.06
        tone = np.sin(2 * math.pi * 880.0 * local_t) * np.exp(-local_t * 14.0) * 0.035
        audio[offset : offset + length] += click + tone

    audio += 0.012 * np.sin(2 * math.pi * 27.5 * timeline)
    fade = int(0.7 * sample_rate)
    audio[:fade] *= np.linspace(0.0, 1.0, fade)
    audio[-fade:] *= np.linspace(1.0, 0.0, fade)
    peak = max(1e-9, float(np.max(np.abs(audio))))
    audio = np.clip(audio / peak * 0.82, -1.0, 1.0)
    stereo = np.column_stack([audio, audio])
    pcm = (stereo * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def ffmpeg_executable() -> Path:
    try:
        import imageio_ffmpeg

        return Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception as exc:
        raise RuntimeError("imageio-ffmpeg is required: python -m pip install --user imageio-ffmpeg==0.6.0") from exc


def render_video(out_dir: Path, metrics: dict[str, object], assets: dict[str, Image.Image]) -> Path:
    ffmpeg = ffmpeg_executable()
    silent_path = out_dir / "lumen_truth_over_hype_silent.mp4"
    audio_path = out_dir / "lumen_truth_over_hype_original_bed.wav"
    final_path = out_dir / "LumenCore_Truth_Over_Hype_TikTok_V1.mp4"
    command = [
        str(ffmpeg),
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(silent_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    repeats = FPS // MOTION_FPS
    frame_count = int(DURATION * MOTION_FPS)
    try:
        for index in range(frame_count):
            frame = render_frame(index / MOTION_FPS, metrics, assets)
            payload = frame.tobytes()
            for _ in range(repeats):
                process.stdin.write(payload)
    finally:
        process.stdin.close()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg video render failed with code {return_code}")

    build_audio(audio_path)
    combine = [
        str(ffmpeg),
        "-y",
        "-i",
        str(silent_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(final_path),
    ]
    subprocess.run(combine, check=True)
    silent_path.unlink(missing_ok=True)
    return final_path


def write_support_files(out_dir: Path, metrics: dict[str, object], receipt_payload: dict[str, object]) -> None:
    voiceover = (
        "Most AI demos only show the win. Ours found a promising one point four five percent result, "
        "then rejected it. Why? Against the strongest baseline for every pair, the mean fell to negative "
        "point two nine percent. Eleven of twenty pairs were positive. The gate required twelve. Zero were "
        "promoted after uncertainty and multiple-testing checks. So the system disabled economic action. "
        "That is LumenCore: not a claim machine, a measurement system. Independent reviewers: run the blind kit."
    )
    caption = (
        "The result looked positive until the stronger test asked a better question. "
        "LumenCore rejected its own signal, blocked economic action, and sealed the receipts. "
        "Source-authentic Kraken public data; not Kraken-endorsed, not independently validated, and not investment advice. "
        "Independent reviewers: the blind reproduction kit is ready.\n\n"
        "#MachineLearning #OpenScience #Reproducibility #QuantResearch #AIAudit #LumenCore"
    )
    subtitles = """1
00:00:00,000 --> 00:00:03,400
My AI found +1.45%. Then it said: don't trade.

2
00:00:03,400 --> 00:00:07,200
Most AI demos only show the win. We built a system that can stop itself.

3
00:00:07,200 --> 00:00:11,400
The diagnostic result was positive. The reviewer-grade result was negative.

4
00:00:11,400 --> 00:00:15,200
Twenty fixed pairs. Seven hundred nineteen returns each. Thirty percent untouched holdout.

5
00:00:15,200 --> 00:00:19,100
Eleven of twenty pairs were positive. The gate required twelve.

6
00:00:19,100 --> 00:00:23,300
All five promotion checks failed. Zero of twenty were promoted.

7
00:00:23,300 --> 00:00:27,200
Duplicates blocked. Sources hashed. Receipts chained. Economic action disabled.

8
00:00:27,200 --> 00:00:32,000
Truth over hype. Independent reviewers: run the blind kit.
"""
    (out_dir / "VOICEOVER_SCRIPT.txt").write_text(voiceover + "\n", encoding="utf-8")
    (out_dir / "TIKTOK_CAPTION.txt").write_text(caption + "\n", encoding="utf-8")
    (out_dir / "SUBTITLES.srt").write_text(subtitles, encoding="utf-8")
    checklist = """# TikTok Upload Checklist

- Format: 1080x1920, 9:16, H.264 video, AAC audio.
- Keep the original on-screen captions enabled.
- Optional: record the supplied voiceover or use TikTok text-to-speech.
- Do not describe the result as validated alpha, official approval, or a trading recommendation.
- Do not remove the source-authentic / independent-review-pending disclosure.
- Suggested cover text: MY AI SAID DON'T TRADE.
- Review the final account, caption, privacy setting, and cover before posting.
"""
    (out_dir / "UPLOAD_CHECKLIST.md").write_text(checklist, encoding="utf-8")

    manifest = {
        "schema": "lumencore_tiktok_truth_video_manifest_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": {
            "source_authentic": True,
            "independently_validated": False,
            "execution_authorized": False,
            "capital_at_risk_allowed": False,
            "decision": metrics["decision"],
        },
        "metrics": metrics,
        "source_receipt": {
            "path": str(RECEIPT),
            "sha256": sha256(RECEIPT),
            "schema": receipt_payload.get("schema"),
        },
        "visual_sources": [
            {"name": name, "path": str(path), "sha256": sha256(path)} for name, path in ASSETS.items()
        ],
        "render": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "duration_seconds": DURATION,
            "audio": "original deterministic synth bed; no copyrighted melody or sampled recording",
        },
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def save_qa_frames(out_dir: Path, metrics: dict[str, object], assets: dict[str, Image.Image]) -> None:
    qa_dir = out_dir / "qa_frames"
    qa_dir.mkdir(parents=True, exist_ok=True)
    times = [1.2, 5.2, 9.0, 13.0, 17.0, 21.0, 25.0, 29.0]
    for index, second in enumerate(times, start=1):
        render_frame(second, metrics, assets).save(qa_dir / f"scene_{index:02d}_{second:04.1f}s.png", optimize=True)
    render_frame(1.2, metrics, assets).save(out_dir / "TIKTOK_COVER.png", optimize=True)


def validate_output(out_dir: Path, video_path: Path) -> dict[str, object]:
    ffmpeg = ffmpeg_executable()
    probe = ffmpeg.with_name("ffprobe.exe")
    probe_candidate = shutil.which("ffprobe")
    if not probe.exists() and probe_candidate:
        probe = Path(probe_candidate)
    if probe.exists():
        command = [
            str(probe),
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=index,codec_name,codec_type,width,height,r_frame_rate",
            "-of",
            "json",
            str(video_path),
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        probe_payload = json.loads(result.stdout)
        validation_backend = "ffprobe"
    else:
        import imageio_ffmpeg

        reader = imageio_ffmpeg.read_frames(str(video_path), pix_fmt="rgb24")
        metadata = next(reader)
        reader.close()
        audio_check = subprocess.run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-i",
                str(video_path),
                "-map",
                "0:a:0",
                "-t",
                "0.25",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        audio_codec = "aac" if "Audio: aac" in audio_check.stderr else "unknown"
        video_codec = str(metadata.get("codec") or "").lower()
        if video_codec == "avc1":
            video_codec = "h264"
        probe_payload = {
            "format": {
                "duration": str(metadata.get("duration", 0.0)),
                "size": str(video_path.stat().st_size),
            },
            "streams": [
                {
                    "index": 0,
                    "codec_name": video_codec,
                    "codec_type": "video",
                    "width": int(metadata.get("size", (0, 0))[0]),
                    "height": int(metadata.get("size", (0, 0))[1]),
                    "r_frame_rate": str(metadata.get("fps", 0.0)),
                },
                {
                    "index": 1,
                    "codec_name": audio_codec,
                    "codec_type": "audio",
                    "decode_check_return_code": audio_check.returncode,
                },
            ],
        }
        validation_backend = "imageio_ffmpeg_metadata_plus_audio_decode"
    streams = probe_payload.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    failures: list[str] = []
    if len(video_streams) != 1:
        failures.append("exactly one video stream required")
    if len(audio_streams) != 1:
        failures.append("exactly one audio stream required")
    if video_streams:
        stream = video_streams[0]
        if int(stream.get("width", 0)) != WIDTH or int(stream.get("height", 0)) != HEIGHT:
            failures.append("video dimensions are not 1080x1920")
        if stream.get("codec_name") != "h264":
            failures.append("video codec is not H.264")
    if audio_streams and audio_streams[0].get("codec_name") != "aac":
        failures.append("audio codec is not AAC")
    duration = float(probe_payload.get("format", {}).get("duration", 0.0))
    if not (31.8 <= duration <= 32.2):
        failures.append(f"unexpected duration {duration}")
    if failures:
        raise RuntimeError("Output validation failed: " + "; ".join(failures))
    receipt = {
        "schema": "lumencore_tiktok_render_validation_v1",
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "video": str(video_path),
        "video_sha256": sha256(video_path),
        "validation_backend": validation_backend,
        "probe": probe_payload,
        "qa_frame_count": len(list((out_dir / "qa_frames").glob("*.png"))),
        "claim_safety_checks": {
            "independent_validation_not_claimed": True,
            "economic_action_not_authorized": True,
            "performance_promotion_not_claimed": True,
        },
    }
    (out_dir / "VALIDATION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def finalize_package_manifest(out_dir: Path) -> None:
    manifest_path = out_dir / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    primary_names = [
        "LumenCore_Truth_Over_Hype_TikTok_V1.mp4",
        "TIKTOK_COVER.png",
        "TIKTOK_CAPTION.txt",
        "VOICEOVER_SCRIPT.txt",
        "SUBTITLES.srt",
        "UPLOAD_CHECKLIST.md",
        "VALIDATION_RECEIPT.json",
        "lumen_truth_over_hype_original_bed.wav",
    ]
    artifacts: list[dict[str, object]] = []
    for name in primary_names:
        path = out_dir / name
        if path.exists():
            artifacts.append(
                {
                    "path": name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    qa_files = sorted((out_dir / "qa_frames").glob("*.png"))
    manifest["artifacts"] = artifacts
    manifest["qa_frames"] = [
        {
            "path": str(path.relative_to(out_dir)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in qa_files
    ]
    manifest["package_status"] = "UPLOAD_READY_NOT_PUBLISHED"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the LumenCore truth-over-hype TikTok video package.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--qa-only", action="store_true", help="Generate cover and QA frames without encoding the MP4.")
    parser.add_argument("--validate-only", action="store_true", help="Validate an existing final MP4 without re-encoding it.")
    args = parser.parse_args()

    receipt_payload, metrics = load_and_validate_receipt()
    assets = load_assets()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    write_support_files(out_dir, metrics, receipt_payload)
    save_qa_frames(out_dir, metrics, assets)
    if args.validate_only:
        video_path = out_dir / "LumenCore_Truth_Over_Hype_TikTok_V1.mp4"
        if not video_path.exists():
            raise FileNotFoundError(video_path)
        validation = validate_output(out_dir, video_path)
        finalize_package_manifest(out_dir)
        print(f"VIDEO={video_path}")
        print(f"SHA256={validation['video_sha256']}")
        print(f"VALIDATION={out_dir / 'VALIDATION_RECEIPT.json'}")
        return 0
    if args.qa_only:
        print(f"QA_DIR={out_dir}")
        return 0
    video_path = render_video(out_dir, metrics, assets)
    validation = validate_output(out_dir, video_path)
    finalize_package_manifest(out_dir)
    print(f"VIDEO={video_path}")
    print(f"SHA256={validation['video_sha256']}")
    print(f"VALIDATION={out_dir / 'VALIDATION_RECEIPT.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
