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
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "evidence" / "external_validation" / "frequency_cluster_reviewer_decision_20260716.json"
TEASER = ROOT / "out" / "social" / "tiktok_truth_over_hype_v1_20260716" / "LumenCore_Truth_Over_Hype_TikTok_V1.mp4"
DEFAULT_OUT = ROOT / "out" / "social" / "the_stop_documentary_trailer_v1_20260716"
PUBLIC_RECEIPT = ROOT / "evidence" / "social" / "the_stop_documentary_trailer_v1_20260716.json"

ASSETS = {
    "founder_laptop": Path(r"C:\Users\Novac\Downloads\IMG_6468 (1).jpeg"),
    "github_failure": Path(r"C:\Users\Novac\Pictures\iCloud Photos\Photos\IMG_6794.PNG"),
    "mission_control": ROOT / "output" / "playwright" / "mission_control_reviewer_1440.png",
    "grants_reviewer": ROOT / "output" / "playwright" / "grants-reviewer-desktop-final.png",
}

WIDTH = 1920
HEIGHT = 1080
FPS = 24
MOTION_FPS = 12
DURATION = 84.0

CONVERSATION_MOTIFS = [
    "Can we do an independent result receipt yet?",
    "We only claim facts.",
    "I love integrity checks.",
    "Everything has to be auditable.",
]

NARRATION_TEXT = (
    "Every big idea begins as a promise. Robert kept asking an AI collaborator for more: more tests, "
    "more data, and stronger proof. He calls the collaborator Luma. The rule that mattered most was "
    "simple: we only claim facts. Then one result looked like the breakthrough. A diagnostic comparison "
    "showed a one point four five percent improvement. The stricter protocol asked a harder question, "
    "and the answer went negative. Eleven of twenty pairs were positive. The gate required twelve. "
    "Five promotion checks failed. Zero pairs were promoted. So the system stopped. No trade. No capital "
    "at risk. The failure was hashed, chained, and preserved. That is the story: not a machine that always "
    "wins, but one being built to know when it has not. A blind reproduction kit now waits for an "
    "independent reviewer. Run it. Try to break it. Return the receipt. LumenCore. Measure first."
)

BG = (5, 12, 21)
PANEL = (12, 29, 45)
PANEL_LIGHT = (26, 53, 72)
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


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def ease(value: float) -> float:
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def scene_alpha(t: float, start: float, end: float, edge: float = 0.45) -> float:
    return min(1.0, max(0.0, (t - start) / edge), max(0.0, (end - t) / edge))


def scene_progress(t: float, start: float, end: float) -> float:
    return ease((t - start) / max(0.001, end - start))


def alpha_color(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return (*color, int(clamp(alpha) * 255))


def cover_crop(image: Image.Image, size: tuple[int, int], *, focus_y: float = 0.5) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize(
        (max(target_w, round(image.width * scale)), max(target_h, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (resized.width - target_w) // 2)
    top = round(max(0, resized.height - target_h) * clamp(focus_y))
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
    focus_y: float = 0.5,
    dim: float = 0.0,
    blur: float = 0.0,
    radius: int = 18,
    border: tuple[int, int, int] = TEAL,
) -> None:
    x0, y0, x1, y1 = box
    panel = cover_crop(image, (x1 - x0, y1 - y0), focus_y=focus_y)
    if dim:
        panel = ImageEnhance.Brightness(panel).enhance(max(0.0, 1.0 - dim))
    if blur:
        panel = panel.filter(ImageFilter.GaussianBlur(blur))
    mask = rounded_mask(panel.size, radius)
    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x0 + 12, y0 + 18, x1 + 12, y1 + 18), radius=radius, fill=(0, 0, 0, 120)
    )
    frame.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    frame.paste(panel.convert("RGBA"), (x0, y0), mask)
    ImageDraw.Draw(frame).rounded_rectangle(box, radius=radius, outline=border, width=3)


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
    return len(lines) * (selected_font.size + spacing)


def draw_base(t: float) -> Image.Image:
    frame = Image.new("RGBA", (WIDTH, HEIGHT), (*BG, 255))
    draw = ImageDraw.Draw(frame, "RGBA")
    for x in range(0, WIDTH, 96):
        draw.line((x, 0, x, HEIGHT), fill=(37, 85, 99, 24), width=1)
    for y in range(0, HEIGHT, 96):
        draw.line((0, y, WIDTH, y), fill=(37, 85, 99, 30), width=1)
    scan_x = int((t * 185) % (WIDTH + 320)) - 160
    draw.rectangle((scan_x, 0, scan_x + 5, HEIGHT), fill=(43, 210, 190, 24))
    draw.line((0, 58, WIDTH, 58), fill=TEAL, width=4)
    draw.ellipse((70, 82, 118, 130), outline=TEAL, width=4)
    draw.ellipse((82, 94, 106, 118), fill=CYAN)
    draw.text((140, 77), "LUMENCORE", font=font(30, bold=True), fill=WHITE)
    draw.text((140, 115), "MEASURE FIRST", font=font(17, mono=True), fill=MUTED)
    draw.text((70, 1023), "Synthetic narration | Evidence, not investment advice", font=font(18), fill=MUTED)
    return frame


def draw_quote(frame: Image.Image, text: str, *, y: int, alpha: float, color: tuple[int, int, int] = WHITE) -> None:
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((250, y - 25), '"', font=font(110, bold=True), fill=alpha_color(TEAL, alpha))
    draw_wrapped(draw, text, (350, y), 1250, font(64, bold=True), alpha_color(color, alpha), spacing=14)


def scene_open(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 0.0, 7.0)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((960, 250), "FROM THE BUILD LOG", font=font(22, mono=True), fill=alpha_color(MUTED, alpha), anchor="ma")
    draw_quote(frame, CONVERSATION_MOTIFS[0], y=380, alpha=alpha)
    draw.text((350, 700), "A QUESTION BECAME THE MOVIE.", font=font(36, bold=True), fill=alpha_color(AMBER, alpha))


def scene_build(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 7.0, 16.0)
    progress = scene_progress(t, 7.0, 16.0)
    x_shift = round(24 * progress)
    paste_panel(frame, assets["founder_laptop"], (80 - x_shift, 180, 1020 - x_shift, 900), focus_y=0.5, dim=0.12)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.rounded_rectangle((980, 210, 1840, 850), radius=22, fill=(6, 16, 27, 235), outline=PANEL_LIGHT, width=2)
    draw.text((1040, 275), "THE BUILD", font=font(24, bold=True, mono=True), fill=alpha_color(TEAL, alpha))
    draw_wrapped(draw, "ONE FOUNDER.\nONE AI COLLABORATOR.\nRELENTLESS ITERATION.", (1040, 355), 730, font(55, bold=True), alpha_color(WHITE, alpha), spacing=20)
    draw.text((1040, 720), "Robert calls the collaborator Luma.", font=font(27), fill=alpha_color(MUTED, alpha))


def scene_rule(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 16.0, 24.0)
    progress = scene_progress(t, 16.0, 24.0)
    paste_panel(frame, assets["mission_control"], (760, 170, 1840, 890), focus_y=0.06, dim=0.42, blur=2.0)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.rounded_rectangle((70, 210, 1080, 830), radius=24, fill=(5, 14, 24, 238), outline=TEAL, width=3)
    draw.text((130, 275), "THE RULE", font=font(26, mono=True, bold=True), fill=alpha_color(AMBER, alpha))
    draw_wrapped(draw, CONVERSATION_MOTIFS[1], (130, 365), 860, font(78, bold=True), alpha_color(WHITE, alpha), spacing=16)
    checks = ["sources hashed", "holdout untouched", "promotion gated", "negative result retained"]
    visible = max(1, min(len(checks), 1 + int(progress * len(checks))))
    for idx, label in enumerate(checks[:visible]):
        y = 610 + idx * 53
        draw.ellipse((133, y + 5, 153, y + 25), fill=GREEN)
        draw.text((175, y), label.upper(), font=font(24, mono=True), fill=alpha_color(MUTED, alpha))


def scene_signal(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 24.0, 34.0)
    progress = scene_progress(t, 24.0, 34.0)
    draw = ImageDraw.Draw(frame, "RGBA")
    if teaser:
        idx = min(len(teaser) - 1, int(progress * len(teaser)))
        panel = teaser[idx]
        paste_panel(frame, panel, (120, 160, 690, 930), focus_y=0.2, dim=0.05, border=CYAN)
    draw.text((800, 205), "THE RESULT LOOKED LIKE A WIN", font=font(28, mono=True, bold=True), fill=alpha_color(MUTED, alpha))
    draw.text((800, 330), f"+{metrics['diagnostic']:.6f}%", font=font(103, bold=True, mono=True), fill=alpha_color(TEAL, alpha))
    draw.text((806, 465), "diagnostic comparison", font=font(31, bold=True), fill=alpha_color(WHITE, alpha))
    draw.line((800, 545, 1760, 545), fill=PANEL_LIGHT, width=3)
    draw_wrapped(draw, "Promising is not promoted.", (800, 625), 850, font(58, bold=True), alpha_color(AMBER, alpha))


def scene_reversal(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 34.0, 44.0)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((110, 205), "THE STRONGER QUESTION CONTROLLED THE DECISION", font=font(31, bold=True), fill=alpha_color(WHITE, alpha))
    cards = [
        ("DIAGNOSTIC", f"+{metrics['diagnostic']:.6f}%", "against one global baseline", TEAL),
        ("REVIEWER GATE", f"{metrics['reviewer']:.6f}%", "against each pair's strongest baseline", RED),
    ]
    for idx, (label, value, note, color) in enumerate(cards):
        x0 = 110 + idx * 875
        draw.rounded_rectangle((x0, 320, x0 + 800, 790), radius=24, fill=(*PANEL, 247), outline=color, width=4)
        draw.text((x0 + 55, 380), label, font=font(28, bold=True, mono=True), fill=alpha_color(color, alpha))
        draw.text((x0 + 55, 485), value, font=font(76, bold=True, mono=True), fill=alpha_color(WHITE, alpha))
        draw_wrapped(draw, note, (x0 + 55, 625), 680, font(30), alpha_color(MUTED, alpha))
    draw.text((960, 900), "THE REVIEWER GATE WON.", font=font(39, bold=True), fill=alpha_color(AMBER, alpha), anchor="ma")


def scene_one_pair(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 44.0, 53.0)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((100, 190), "THE GATE MISSED BY ONE PAIR", font=font(48, bold=True), fill=alpha_color(WHITE, alpha))
    positive = int(metrics["positive"])
    total = int(metrics["total"])
    required = math.ceil(float(metrics["required_fraction"]) * total)
    for index in range(total):
        col = index % 10
        row = index // 10
        cx = 170 + col * 165
        cy = 410 + row * 190
        color = TEAL if index < positive else (66, 84, 98)
        draw.ellipse((cx - 42, cy - 42, cx + 42, cy + 42), fill=alpha_color(color, alpha), outline=WHITE, width=2)
        draw.text((cx, cy), str(index + 1), font=font(23, bold=True), fill=BG, anchor="mm")
    draw.rounded_rectangle((250, 780, 1670, 945), radius=22, fill=(*PANEL, 248), outline=RED, width=3)
    draw.text((335, 830), f"OBSERVED {positive}/{total}", font=font(42, bold=True, mono=True), fill=alpha_color(WHITE, alpha))
    draw.text((1045, 830), f"REQUIRED {required}/{total}", font=font(42, bold=True, mono=True), fill=alpha_color(RED, alpha))


def scene_gauntlet(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 53.0, 62.0)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((90, 190), "FIVE PROMOTION CHECKS. FIVE FAILS.", font=font(48, bold=True), fill=alpha_color(WHITE, alpha))
    checks = [
        "aggregate pair effect positive",
        "bootstrap lower bound positive",
        "minimum positive-pair fraction",
        "leave-one-pair-out positive",
        "minimum individually promoted pairs",
    ]
    for idx, label in enumerate(checks):
        col = idx % 2
        row = idx // 2
        x0 = 90 + col * 900
        y0 = 320 + row * 205
        draw.rounded_rectangle((x0, y0, x0 + 830, y0 + 155), radius=18, fill=(*PANEL, 247), outline=PANEL_LIGHT, width=2)
        draw.ellipse((x0 + 35, y0 + 47, x0 + 95, y0 + 107), fill=RED)
        draw.line((x0 + 52, y0 + 64, x0 + 78, y0 + 90), fill=WHITE, width=6)
        draw.line((x0 + 78, y0 + 64, x0 + 52, y0 + 90), fill=WHITE, width=6)
        draw.text((x0 + 130, y0 + 54), label.upper(), font=font(24, bold=True, mono=True), fill=alpha_color(WHITE, alpha))
    draw.text((1430, 832), f"{metrics['promoted']}/20 PROMOTED", font=font(45, bold=True, mono=True), fill=alpha_color(RED, alpha), anchor="ma")


def scene_integrity(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 62.0, 71.0)
    paste_panel(frame, assets["github_failure"], (1110, 145, 1820, 920), focus_y=0.1, dim=0.46)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.rounded_rectangle((70, 190, 1260, 880), radius=25, fill=(5, 14, 24, 238), outline=TEAL, width=3)
    draw_wrapped(draw, CONVERSATION_MOTIFS[2], (130, 260), 940, font(63, bold=True), alpha_color(WHITE, alpha))
    rows = [
        ("DUPLICATE INPUT", "BLOCKED", RED),
        ("SOURCE SNAPSHOT", "HASHED", TEAL),
        ("EVIDENCE RECEIPTS", "CHAINED", TEAL),
        ("ECONOMIC ACTION", "DISABLED", RED),
    ]
    for idx, (label, value, color) in enumerate(rows):
        y = 470 + idx * 88
        draw.text((135, y), label, font=font(23, mono=True), fill=alpha_color(MUTED, alpha))
        draw.text((615, y - 5), value, font=font(31, bold=True, mono=True), fill=alpha_color(color, alpha))
    draw.text((130, 820), "FAILURE IS DATA.", font=font(31, bold=True), fill=alpha_color(AMBER, alpha))


def scene_handoff(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 71.0, 78.0)
    paste_panel(frame, assets["grants_reviewer"], (940, 160, 1830, 900), focus_y=0.04, dim=0.45, blur=1.0)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((100, 190), "THE HANDOFF", font=font(28, bold=True, mono=True), fill=alpha_color(TEAL, alpha))
    draw_wrapped(draw, "BLIND REPRODUCTION KIT", (100, 290), 980, font(69, bold=True), alpha_color(WHITE, alpha), spacing=10)
    draw.text((105, 500), "INTEGRITY CHECK", font=font(23, mono=True), fill=alpha_color(MUTED, alpha))
    draw.text((105, 550), "PASS", font=font(50, bold=True, mono=True), fill=alpha_color(GREEN, alpha))
    draw.text((105, 660), "EXTERNAL EXECUTION", font=font(23, mono=True), fill=alpha_color(MUTED, alpha))
    draw.text((105, 710), "PENDING", font=font(50, bold=True, mono=True), fill=alpha_color(AMBER, alpha))
    draw_wrapped(draw, "No validation is claimed before an outsider returns a receipt.", (105, 835), 760, font(27, bold=True), alpha_color(WHITE, alpha))


def scene_close(frame: Image.Image, t: float, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    alpha = scene_alpha(t, 78.0, DURATION, edge=0.6)
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.text((960, 235), "THE STOP", font=font(115, bold=True), fill=alpha_color(WHITE, alpha), anchor="ma")
    draw.text((960, 385), "WHEN THE STRONGER TEST SAYS NO", font=font(38, bold=True, mono=True), fill=alpha_color(TEAL, alpha), anchor="ma")
    draw.line((430, 485, 1490, 485), fill=PANEL_LIGHT, width=3)
    draw_wrapped(
        draw,
        "Independent reviewers: run the kit. Try to break it. Return the receipt.",
        (960, 580),
        1250,
        font(48, bold=True),
        alpha_color(WHITE, alpha),
        spacing=12,
        anchor="ma",
    )
    draw.text((960, 820), "lumen-core.ai", font=font(48, bold=True), fill=alpha_color(CYAN, alpha), anchor="ma")
    draw.text((960, 890), "INDEPENDENT REVIEW PENDING", font=font(24, bold=True, mono=True), fill=alpha_color(AMBER, alpha), anchor="ma")


def render_frame(
    t: float,
    metrics: dict[str, Any],
    assets: dict[str, Image.Image],
    teaser_frames: list[Image.Image],
) -> Image.Image:
    frame = draw_base(t)
    if t < 7.0:
        scene_open(frame, t, metrics, assets, teaser_frames)
    elif t < 16.0:
        scene_build(frame, t, metrics, assets, teaser_frames)
    elif t < 24.0:
        scene_rule(frame, t, metrics, assets, teaser_frames)
    elif t < 34.0:
        scene_signal(frame, t, metrics, assets, teaser_frames)
    elif t < 44.0:
        scene_reversal(frame, t, metrics, assets, teaser_frames)
    elif t < 53.0:
        scene_one_pair(frame, t, metrics, assets, teaser_frames)
    elif t < 62.0:
        scene_gauntlet(frame, t, metrics, assets, teaser_frames)
    elif t < 71.0:
        scene_integrity(frame, t, metrics, assets, teaser_frames)
    elif t < 78.0:
        scene_handoff(frame, t, metrics, assets, teaser_frames)
    else:
        scene_close(frame, t, metrics, assets, teaser_frames)
    return frame.convert("RGB")


def load_and_validate_receipt() -> tuple[dict[str, Any], dict[str, Any]]:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    expected = "NULL_OR_ADVERSE_NOT_PROMOTED_DO_NOT_RUN_ECONOMIC_ACTION"
    failures: list[str] = []
    if payload.get("decision") != expected:
        failures.append("unexpected decision")
    if payload.get("execution_authorized") is not False:
        failures.append("execution must remain unauthorized")
    if payload.get("capital_at_risk_allowed") is not False:
        failures.append("capital at risk must remain disallowed")
    if payload.get("independently_validated") is not False:
        failures.append("independent validation must remain pending")
    official = payload.get("official_source", {})
    if not isinstance(official, dict) or official.get("source_authentic") is not True:
        failures.append("source-authentic receipt missing")
    gate = payload.get("reviewer_grade_gate", {})
    if not isinstance(gate, dict) or gate.get("gate_pass") is not False:
        failures.append("reviewer gate must remain failed")
    blind = payload.get("blind_reproduction", {})
    if not isinstance(blind, dict) or blind.get("zip_integrity_passed") is not True:
        failures.append("blind kit integrity did not pass")
    if failures:
        raise RuntimeError("Claim-safety check failed: " + "; ".join(failures))
    diagnostic = payload["diagnostic_global_comparison"]
    metrics = {
        "diagnostic": float(diagnostic["improvement_pct_vs_one_global_strongest_named_baseline"]),
        "reviewer": float(gate["mean_pair_improvement_pct"]),
        "positive": int(gate["positive_pairs"]),
        "total": int(gate["total_pairs"]),
        "required_fraction": float(gate["required_positive_pair_fraction"]),
        "promoted": len(gate["individually_promoted_pairs"]),
        "decision": payload["decision"],
        "kit_integrity_passed": bool(blind["zip_integrity_passed"]),
        "external_status": blind["external_execution_status"],
    }
    return payload, metrics


def load_assets() -> dict[str, Image.Image]:
    missing = [str(path) for path in ASSETS.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing visual assets: " + ", ".join(missing))
    return {name: ImageOps.exif_transpose(Image.open(path)).convert("RGB") for name, path in ASSETS.items()}


def ffmpeg_executable() -> Path:
    try:
        import imageio_ffmpeg

        return Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception as exc:
        raise RuntimeError("imageio-ffmpeg is required") from exc


def extract_teaser_frames(out_dir: Path) -> list[Image.Image]:
    if not TEASER.is_file():
        raise FileNotFoundError(f"Selected teaser is missing: {TEASER}")
    frame_dir = out_dir / "_teaser_frames"
    shutil.rmtree(frame_dir, ignore_errors=True)
    frame_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg_executable()),
        "-y",
        "-ss",
        "0",
        "-t",
        "8",
        "-i",
        str(TEASER),
        "-vf",
        "fps=8,scale=480:854",
        str(frame_dir / "frame_%03d.png"),
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    paths = sorted(frame_dir.glob("frame_*.png"))
    if len(paths) < 32:
        raise RuntimeError("Teaser frame extraction produced too few frames")
    frames = [Image.open(path).convert("RGB").copy() for path in paths]
    shutil.rmtree(frame_dir, ignore_errors=True)
    return frames


def build_audio_bed(path: Path) -> None:
    sample_rate = 48_000
    count = int(DURATION * sample_rate)
    timeline = np.arange(count, dtype=np.float64) / sample_rate
    audio = np.zeros(count, dtype=np.float64)
    rng = np.random.default_rng(20260716)
    bpm = 92.0
    beat_seconds = 60.0 / bpm
    progression = [41.203, 48.999, 55.0, 36.708]
    for beat_index, start in enumerate(np.arange(0.0, DURATION, beat_seconds)):
        offset = int(start * sample_rate)
        length = min(int(0.42 * sample_rate), count - offset)
        local_t = np.arange(length, dtype=np.float64) / sample_rate
        kick = np.sin(2 * math.pi * (52.0 * local_t + 35.0 * local_t * np.exp(-local_t * 18.0)))
        kick *= np.exp(-local_t * 11.0) * 0.23
        audio[offset : offset + length] += kick
        note = progression[(beat_index // 4) % len(progression)]
        pad_length = min(int(beat_seconds * 4.1 * sample_rate), count - offset)
        pad_t = np.arange(pad_length, dtype=np.float64) / sample_rate
        envelope = np.minimum(1.0, pad_t * 2.0) * np.exp(-pad_t * 0.40)
        pad = (
            np.sin(2 * math.pi * note * pad_t)
            + 0.45 * np.sin(2 * math.pi * note * 1.5 * pad_t)
            + 0.20 * np.sin(2 * math.pi * note * 2.0 * pad_t)
        )
        audio[offset : offset + pad_length] += pad * envelope * 0.026
    for start in (7, 16, 24, 34, 44, 53, 62, 71, 78):
        offset = int(start * sample_rate)
        length = min(int(0.75 * sample_rate), count - offset)
        local_t = np.arange(length, dtype=np.float64) / sample_rate
        impact = rng.normal(0.0, 1.0, length) * np.exp(-local_t * 8.0) * 0.045
        impact += np.sin(2 * math.pi * 68.0 * local_t) * np.exp(-local_t * 5.5) * 0.11
        audio[offset : offset + length] += impact
    audio += 0.006 * np.sin(2 * math.pi * 27.5 * timeline)
    fade = int(1.2 * sample_rate)
    audio[:fade] *= np.linspace(0.0, 1.0, fade)
    audio[-fade:] *= np.linspace(1.0, 0.0, fade)
    peak = max(1e-9, float(np.max(np.abs(audio))))
    stereo = np.column_stack([np.clip(audio / peak * 0.78, -1.0, 1.0)] * 2)
    pcm = (stereo * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def write_support_files(out_dir: Path, metrics: dict[str, Any], receipt_payload: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "NARRATION_SCRIPT.txt").write_text(NARRATION_TEXT + "\n", encoding="utf-8")
    subtitles = """1
00:00:00,000 --> 00:00:07,000
Can we do an independent result receipt yet?

2
00:00:07,000 --> 00:00:16,000
One founder. One AI collaborator. Relentless iteration.

3
00:00:16,000 --> 00:00:24,000
The rule: we only claim facts.

4
00:00:24,000 --> 00:00:34,000
A diagnostic comparison showed a promising +1.446923%.

5
00:00:34,000 --> 00:00:44,000
The stricter reviewer-grade comparison was -0.287158%.

6
00:00:44,000 --> 00:00:53,000
Eleven of twenty pairs were positive. The gate required twelve.

7
00:00:53,000 --> 00:01:02,000
Five promotion checks failed. Zero pairs were promoted.

8
00:01:02,000 --> 00:01:11,000
The system stopped. The failure was hashed, chained, and preserved.

9
00:01:11,000 --> 00:01:18,000
A blind reproduction kit waits for an independent reviewer.

10
00:01:18,000 --> 00:01:24,000
Run it. Try to break it. Return the receipt.
"""
    (out_dir / "SUBTITLES.srt").write_text(subtitles, encoding="utf-8")
    readme = """# The Stop - Documentary Trailer Package

- Working title: **The Stop: When the Stronger Test Says No**
- Format: 1920x1080, 16:9, H.264 video, AAC audio.
- Narration: synthetic voice; the exact engine and voice are disclosed in the manifest.
- Music: original deterministic synthesis; no sampled recording or copyrighted melody.
- Public boundary: no independent validation, promoted performance, trading recommendation, or permission to risk capital is claimed.
- Long personal footage and provenance-ambiguous controller clips remain frozen from the public surface.
- Status: rendered package only; not posted or distributed by this builder.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    manifest = {
        "schema": "lumencore_the_stop_documentary_manifest_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "title": "The Stop: When the Stronger Test Says No",
        "claim_boundary": {
            "source_authentic": True,
            "independently_validated": False,
            "execution_authorized": False,
            "capital_at_risk_allowed": False,
            "decision": metrics["decision"],
        },
        "conversation_motifs": CONVERSATION_MOTIFS,
        "metrics": metrics,
        "source_receipt": {
            "repo_path": str(RECEIPT.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(RECEIPT),
            "schema": receipt_payload.get("schema"),
        },
        "selected_video": {
            "repo_path": str(TEASER.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(TEASER),
            "purpose": "Previously validated teaser used as a motion insert.",
        },
        "visual_sources": [
            {"asset_id": name, "sha256": sha256(path), "path_disclosed_publicly": False}
            for name, path in ASSETS.items()
        ],
        "frozen_from_public_cut": [
            "physical_context_long_video",
            "legacy_controller_live_photo_01",
            "legacy_controller_live_photo_02",
        ],
        "render": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "duration_seconds": DURATION,
            "music": "original deterministic synth bed",
            "narration_disclosure": "synthetic narration",
        },
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def save_qa_frames(out_dir: Path, metrics: dict[str, Any], assets: dict[str, Image.Image], teaser: list[Image.Image]) -> None:
    qa_dir = out_dir / "qa_frames"
    qa_dir.mkdir(parents=True, exist_ok=True)
    times = [2.5, 10.5, 19.0, 28.0, 38.0, 47.5, 56.5, 65.5, 74.0, 81.0]
    for index, second in enumerate(times, start=1):
        render_frame(second, metrics, assets, teaser).save(qa_dir / f"scene_{index:02d}_{second:04.1f}s.png", optimize=True)
    render_frame(2.5, metrics, assets, teaser).save(out_dir / "TRAILER_COVER.png", optimize=True)


def render_video(
    out_dir: Path,
    metrics: dict[str, Any],
    assets: dict[str, Image.Image],
    teaser_frames: list[Image.Image],
    narration_path: Path,
) -> Path:
    if not narration_path.is_file():
        raise FileNotFoundError(f"AI narration is required for the final cut: {narration_path}")
    ffmpeg = ffmpeg_executable()
    silent_path = out_dir / "the_stop_silent.mp4"
    bed_path = out_dir / "the_stop_original_bed.wav"
    final_path = out_dir / "LumenCore_The_Stop_Documentary_Trailer_V1.mp4"
    command = [
        str(ffmpeg), "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    repeats = FPS // MOTION_FPS
    try:
        for index in range(int(DURATION * MOTION_FPS)):
            payload = render_frame(index / MOTION_FPS, metrics, assets, teaser_frames).tobytes()
            for _ in range(repeats):
                process.stdin.write(payload)
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg video render failed")
    build_audio_bed(bed_path)
    mix = [
        str(ffmpeg), "-y", "-i", str(silent_path), "-i", str(bed_path), "-i", str(narration_path),
        "-filter_complex", "[1:a]volume=0.22[bed];[2:a]adelay=4500:all=1,volume=1.20[voice];[bed][voice]amix=inputs=2:duration=first:dropout_transition=2[mixed];[mixed]loudnorm=I=-16:LRA=11:TP=-1.5[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "224k", "-ar", "48000", "-t", str(DURATION),
        "-movflags", "+faststart", str(final_path),
    ]
    subprocess.run(mix, check=True)
    silent_path.unlink(missing_ok=True)
    return final_path


def validate_output(out_dir: Path, video_path: Path) -> dict[str, Any]:
    import imageio_ffmpeg

    reader = imageio_ffmpeg.read_frames(str(video_path), pix_fmt="rgb24")
    metadata = next(reader)
    reader.close()
    ffmpeg = ffmpeg_executable()
    audio_check = subprocess.run(
        [str(ffmpeg), "-v", "error", "-i", str(video_path), "-map", "0:a:0", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    stream_probe = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-i", str(video_path)],
        capture_output=True,
        text=True,
    )
    size = tuple(int(value) for value in metadata.get("size", (0, 0)))
    duration = float(metadata.get("duration", 0.0))
    fps = float(metadata.get("fps", 0.0))
    failures: list[str] = []
    if size != (WIDTH, HEIGHT):
        failures.append(f"unexpected size {size}")
    if abs(duration - DURATION) > 0.2:
        failures.append(f"unexpected duration {duration}")
    if abs(fps - FPS) > 0.1:
        failures.append(f"unexpected fps {fps}")
    if audio_check.returncode != 0:
        failures.append("audio stream failed decode check")
    if "Audio: aac" not in stream_probe.stderr:
        failures.append("audio codec is not AAC")
    if "48000 Hz" not in stream_probe.stderr:
        failures.append("audio sample rate is not 48000 Hz")
    if len(list((out_dir / "qa_frames").glob("*.png"))) != 10:
        failures.append("expected ten QA frames")
    receipt = {
        "schema": "lumencore_the_stop_render_validation_v1",
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failures else "FAIL",
        "video_sha256": sha256(video_path),
        "probe": {
            "size": list(size),
            "duration": duration,
            "fps": fps,
            "audio_codec": "aac" if "Audio: aac" in stream_probe.stderr else "unknown",
            "audio_sample_rate_hz": 48000 if "48000 Hz" in stream_probe.stderr else 0,
            "audio_decode_return_code": audio_check.returncode,
        },
        "qa_frame_count": len(list((out_dir / "qa_frames").glob("*.png"))),
        "claim_safety_checks": {
            "independent_validation_not_claimed": True,
            "economic_action_not_authorized": True,
            "performance_promotion_not_claimed": True,
            "synthetic_narration_disclosed": True,
        },
        "failures": failures,
    }
    (out_dir / "VALIDATION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise RuntimeError("Trailer validation failed: " + "; ".join(failures))
    return receipt


def finalize_manifest(
    out_dir: Path,
    narration_path: Path,
    *,
    narration_engine: str,
    narration_voice: str,
) -> dict[str, Any]:
    manifest_path = out_dir / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = []
    for name in [
        "LumenCore_The_Stop_Documentary_Trailer_V1.mp4",
        "TRAILER_COVER.png",
        "NARRATION_SCRIPT.txt",
        "SUBTITLES.srt",
        "README.md",
        "VALIDATION_RECEIPT.json",
        "the_stop_original_bed.wav",
    ]:
        path = out_dir / name
        artifacts.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest["narration"] = {
        "engine": narration_engine,
        "voice": narration_voice,
        "synthetic": True,
        "source_file_name": narration_path.name,
        "sha256": sha256(narration_path),
    }
    manifest["artifacts"] = artifacts
    manifest["qa_frames"] = [
        {"path": f"qa_frames/{path.name}", "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted((out_dir / "qa_frames").glob("*.png"))
    ]
    manifest["package_status"] = "RENDERED_NOT_PUBLISHED"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_public_receipt(path: Path, out_dir: Path, manifest: dict[str, Any], validation: dict[str, Any]) -> None:
    video = out_dir / "LumenCore_The_Stop_Documentary_Trailer_V1.mp4"
    payload = {
        "schema": "lumencore_the_stop_public_release_receipt_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "title": manifest["title"],
        "status": "RENDERED_NOT_PUBLISHED",
        "video": {"file_name": video.name, "bytes": video.stat().st_size, "sha256": sha256(video)},
        "manifest_sha256": sha256(out_dir / "MANIFEST.json"),
        "validation_receipt_sha256": sha256(out_dir / "VALIDATION_RECEIPT.json"),
        "source_receipt_sha256": manifest["source_receipt"]["sha256"],
        "selected_teaser_sha256": manifest["selected_video"]["sha256"],
        "claim_boundary": manifest["claim_boundary"],
        "validation_status": validation["status"],
        "synthetic_narration_disclosed": True,
        "frozen_asset_ids": manifest["frozen_from_public_cut"],
        "source_files_mutated": False,
        "distribution_performed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the evidence-first LumenCore documentary trailer.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--narration", type=Path)
    parser.add_argument("--narration-engine", default="externally supplied synthetic narration")
    parser.add_argument("--narration-voice", default="unspecified synthetic voice")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--qa-only", action="store_true")
    parser.add_argument("--skip-public-receipt", action="store_true")
    args = parser.parse_args()
    out_dir = args.out.resolve()
    payload, metrics = load_and_validate_receipt()
    write_support_files(out_dir, metrics, payload)
    if args.prepare_only:
        print(out_dir / "NARRATION_SCRIPT.txt")
        return 0
    narration = args.narration.resolve() if args.narration else out_dir / "AI_NARRATION_CEDAR.wav"
    assets = load_assets()
    teaser_frames = extract_teaser_frames(out_dir)
    save_qa_frames(out_dir, metrics, assets, teaser_frames)
    if args.qa_only:
        print(out_dir / "qa_frames")
        return 0
    video = render_video(out_dir, metrics, assets, teaser_frames, narration)
    validation = validate_output(out_dir, video)
    manifest = finalize_manifest(
        out_dir,
        narration,
        narration_engine=args.narration_engine,
        narration_voice=args.narration_voice,
    )
    if not args.skip_public_receipt:
        write_public_receipt(PUBLIC_RECEIPT, out_dir, manifest, validation)
    print(video)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
