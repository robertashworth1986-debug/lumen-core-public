from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = ROOT / "output" / "video" / "prooflock_console_build_week_v2"
SOURCE_DIR = WORK_DIR / "frames"
SLIDE_DIR = WORK_DIR / "slides"
SEGMENT_DIR = WORK_DIR / "segments"
NARRATION_PATH = ROOT / "output" / "speech" / "prooflock_console_build_week_narration_v2.wav"
OUTPUT_PATH = WORK_DIR / "prooflock_console_openai_build_week_demo_v2.mp4"
RECEIPT_PATH = WORK_DIR / "prooflock_console_openai_build_week_demo_v2.receipt.json"
THUMBNAIL_PATH = WORK_DIR / "prooflock_console_devpost_thumbnail_v2.png"
CONCAT_PATH = WORK_DIR / "slides.concat.txt"

WIDTH = 1920
HEIGHT = 1080
BACKGROUND = "#0a0d12"
PANEL = "#121821"
TEXT = "#f5f7fa"
MUTED = "#aab5c1"
GREEN = "#5be0a5"
AMBER = "#ffb454"
RED = "#ff6f70"
BLUE = "#67b8ff"
DEEP_LINE = "#18222d"
MID_LINE = "#263342"

FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_MONO = Path(r"C:\Windows\Fonts\consola.ttf")

SLIDE_SPECS = (
    ("01_boundary.png", 10.0),
    ("02_verified.png", 18.0),
    ("03_separation.png", 18.0),
    ("04_authority_attack.png", 32.0),
    ("05_restored.png", 14.0),
    ("06_reproducibility.png", 22.0),
    ("07_codex_boundary.png", 10.0),
    ("08_close.png", 2.0),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def fit_contain(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    target_width = box[2] - box[0]
    target_height = box[3] - box[1]
    scale = min(target_width / image.width, target_height / image.height)
    resized = image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    contained = Image.new("RGB", (target_width, target_height), "#0d1219")
    offset = ((target_width - resized.width) // 2, (target_height - resized.height) // 2)
    contained.paste(resized, offset)
    return contained


def paste_panel(canvas: Image.Image, source: Image.Image, box: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=8, fill=PANEL, outline="#26313d", width=2)
    inset = 8
    inner = (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset)
    canvas.paste(fit_contain(source, inner), (inner[0], inner[1]))


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, color: str = TEXT,
         bold: bool = False, mono: bool = False) -> None:
    path = FONT_MONO if mono else (FONT_BOLD if bold else FONT_REGULAR)
    draw.text(xy, value, font=font(path, size), fill=color)


def wrap(draw: ImageDraw.ImageDraw, value: str, max_width: int, size: int, *, bold: bool = False,
         mono: bool = False) -> list[str]:
    path = FONT_MONO if mono else (FONT_BOLD if bold else FONT_REGULAR)
    active_font = font(path, size)
    lines: list[str] = []
    current = ""
    for word in value.split():
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=active_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def paragraph(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, max_width: int, size: int,
              color: str = MUTED, line_gap: int = 12, bold: bool = False) -> int:
    y = xy[1]
    for line in wrap(draw, value, max_width, size, bold=bold):
        text(draw, (xy[0], y), line, size, color=color, bold=bold)
        y += size + line_gap
    return y


def draw_evidence_mesh(canvas: Image.Image, accent: str, phase: int) -> None:
    draw = ImageDraw.Draw(canvas)
    center_x, center_y = 1570, 760
    for index in range(7):
        radius_x = 170 + index * 48
        radius_y = 82 + index * 27
        start = 198 + phase * 7 + index * 11
        draw.arc(
            (center_x - radius_x, center_y - radius_y, center_x + radius_x, center_y + radius_y),
            start=start,
            end=start + 118,
            fill=accent if index in {1, 5} else DEEP_LINE,
            width=2 if index in {1, 5} else 1,
        )
    points: list[tuple[int, int]] = []
    for index in range(9):
        angle = math.radians(198 + index * 17 + phase * 3)
        x = int(center_x + math.cos(angle) * (190 + index * 24))
        y = int(center_y + math.sin(angle) * (90 + index * 12))
        points.append((x, y))
    for first, second in zip(points, points[1:]):
        draw.line((*first, *second), fill=MID_LINE, width=1)
    for x, y in points[1:-1:2]:
        draw.rectangle((x - 3, y - 3, x + 3, y + 3), fill=accent)


def draw_corona_mark(canvas: Image.Image, center: tuple[int, int], radius: int) -> None:
    draw = ImageDraw.Draw(canvas)
    cx, cy = center
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=MID_LINE, width=2)
    draw.arc((cx - radius, cy - radius, cx + radius, cy + radius), 206, 316, fill=GREEN, width=10)
    draw.arc((cx - radius + 24, cy - radius + 24, cx + radius - 24, cy + radius - 24), 332, 66, fill=BLUE, width=7)
    draw.arc((cx - radius + 48, cy - radius + 48, cx + radius - 48, cy + radius - 48), 78, 188, fill=AMBER, width=7)
    draw.line((cx - radius + 42, cy, cx + radius - 42, cy), fill=MID_LINE, width=2)
    draw.line((cx, cy - radius + 42, cx, cy + radius - 42), fill=MID_LINE, width=2)
    draw.rectangle((cx - 10, cy - 10, cx + 10, cy + 10), fill=BACKGROUND, outline=TEXT, width=2)
    for x, y, color in (
        (cx - radius + 58, cy + 45, GREEN),
        (cx + 52, cy - radius + 58, BLUE),
        (cx + radius - 62, cy + 32, AMBER),
    ):
        draw.rectangle((x - 5, y - 5, x + 5, y + 5), fill=color)


def draw_progress(draw: ImageDraw.ImageDraw, step: int, accent: str) -> None:
    start_x = 1604
    for index in range(8):
        color = accent if index <= step else MID_LINE
        draw.rectangle((start_x + index * 28, 1046, start_x + index * 28 + 18, 1050), fill=color)
    text(draw, (1468, 1024), f"0{step + 1} / 08", 15, color=MUTED, mono=True)


def build_thumbnail() -> Path:
    width, height = 1500, 1000
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, 10), fill=GREEN)

    # A sparse evidence lattice gives the mark depth without competing with the copy.
    nodes = ((860, 152), (1060, 106), (1300, 174), (1404, 398), (1274, 650), (1020, 720), (842, 574))
    for index, first in enumerate(nodes):
        second = nodes[(index + 1) % len(nodes)]
        draw.line((*first, *second), fill=DEEP_LINE, width=3)
        draw.line((*first, 1135, 390), fill=MID_LINE, width=1)
        draw.rectangle((first[0] - 5, first[1] - 5, first[0] + 5, first[1] + 5), fill=BLUE)
    for radius in (120, 190, 270):
        draw.arc((1135 - radius, 390 - radius, 1135 + radius, 390 + radius), 198, 334, fill=MID_LINE, width=2)
    draw_corona_mark(canvas, (1135, 390), 220)

    text(draw, (72, 62), "BUILD WEEK DEMO", 24, color=GREEN, bold=True)
    text(draw, (72, 112), "ProofLock", 72, bold=True)
    text(draw, (72, 190), "Console", 72, bold=True)
    paragraph(draw, (72, 302), "Hash what exists. Hold what is not proven.", 650, 35, color=MUTED)

    badges = (
        ("RECEIPT", "VERIFIED", GREEN),
        ("POLICY", "FAIL-CLOSED", AMBER),
        ("VERIFIER", "PUBLIC", BLUE),
    )
    x = 72
    for label, value, color in badges:
        draw.rounded_rectangle((x, 456, x + 204, 556), radius=8, fill=PANEL, outline=color, width=2)
        text(draw, (x + 20, 474), label, 16, color=MUTED, bold=True)
        text(draw, (x + 20, 508), value, 20, color=color, bold=True)
        x += 222

    draw.rounded_rectangle((72, 702, 1428, 890), radius=8, fill=PANEL, outline="#344252", width=2)
    text(draw, (108, 736), "EVIDENCE BEFORE CLAIMS", 22, color=GREEN, bold=True)
    paragraph(
        draw,
        (108, 784),
        "Canonical SHA-256 receipts, artifact custody, adversarial tamper checks, and explicit authority gates.",
        1220,
        29,
        color=TEXT,
    )
    text(draw, (72, 946), "Integrity verification and gate logic. No external-validation claim.", 20, color=MUTED)

    THUMBNAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = THUMBNAIL_PATH.with_suffix(".png.tmp")
    canvas.save(temporary, format="PNG", optimize=True)
    os.replace(temporary, THUMBNAIL_PATH)
    return THUMBNAIL_PATH


def base_slide(kicker: str, title_value: str, accent: str = GREEN, step: int = 0) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw_evidence_mesh(canvas, accent, step)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, WIDTH, 8), fill=accent)
    text(draw, (72, 48), kicker.upper(), 22, color=accent, bold=True)
    text(draw, (72, 82), title_value, 48, bold=True)
    draw_progress(draw, step, accent)
    return canvas, draw


def crop_top(path: Path, height: int = 900) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return image.crop((0, 0, image.width, min(height, image.height)))


def crop_bottom(path: Path, height: int = 520) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return image.crop((0, max(0, image.height - height), image.width, image.height))


def save_slide(name: str, canvas: Image.Image) -> Path:
    SLIDE_DIR.mkdir(parents=True, exist_ok=True)
    path = SLIDE_DIR / name
    canvas.save(path, format="PNG", optimize=True)
    return path


def build_slides(public_commit: str, test_evidence: str) -> list[Path]:
    required_sources = {
        "initial": SOURCE_DIR / "01_current_initial.png",
        "authority_attack": SOURCE_DIR / "02_current_authority_attack.png",
        "restored": SOURCE_DIR / "03_current_restored.png",
    }
    missing = [str(path) for path in required_sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing captured source frame(s): {missing}")

    built: list[Path] = []

    canvas, draw = base_slide("ProofLock Console", "Hash what exists. Hold what is not proven.", GREEN, 0)
    paragraph(
        draw,
        (72, 174),
        "A public developer tool that separates artifact integrity from authority to make a claim.",
        820,
        32,
        color=MUTED,
    )
    paste_panel(canvas, crop_top(required_sources["initial"], 760), (980, 138, 1848, 914))
    text(draw, (72, 882), "LOCAL REHEARSAL - PUBLIC RELEASE HELD", 18, color=AMBER, bold=True)
    text(draw, (72, 920), public_commit, 22, color=TEXT, mono=True)
    built.append(save_slide("01_boundary.png", canvas))

    canvas, draw = base_slide("Canonical verification", "Integrity passes. Authority remains held.", GREEN, 1)
    paste_panel(canvas, crop_top(required_sources["initial"], 620), (72, 154, 1848, 872))
    draw.rounded_rectangle((72, 936, 570, 1014), radius=8, fill=PANEL, outline=GREEN, width=2)
    draw.rounded_rectangle((612, 936, 1190, 1014), radius=8, fill=PANEL, outline=AMBER, width=2)
    draw.rounded_rectangle((1232, 936, 1848, 1014), radius=8, fill=PANEL, outline=AMBER, width=2)
    text(draw, (100, 958), "4 / 4 artifacts matched", 25, color=GREEN, bold=True)
    text(draw, (644, 958), "4 authority gates held", 25, color=AMBER, bold=True)
    text(draw, (1264, 958), "Effective decision: HOLD", 25, color=AMBER, bold=True)
    built.append(save_slide("02_verified.png", canvas))

    canvas, draw = base_slide("Three independent questions", "Integrity is not evidence. Evidence is not authority.", AMBER, 2)
    columns = (
        ("INTEGRITY", "Did the bytes and canonical receipt stay unchanged?", GREEN),
        ("EVIDENCE", "Do the matched artifacts support the exact bounded statement?", BLUE),
        ("AUTHORITY", "Did a trusted reviewer approve the release decision?", AMBER),
    )
    x = 72
    for label, body, color in columns:
        draw.rounded_rectangle((x, 202, x + 548, 708), radius=8, fill=PANEL, outline=color, width=3)
        text(draw, (x + 34, 242), label, 22, color=color, bold=True)
        paragraph(draw, (x + 34, 316), body, 470, 31, color=TEXT)
        draw.line((x + 34, 530, x + 514, 530), fill=MID_LINE, width=2)
        footer = "HASH AND PATH CHECKS" if label == "INTEGRITY" else ("CLAIM-SCOPED SUPPORT" if label == "EVIDENCE" else "TRUSTED EXTERNAL OR HUMAN GATE")
        paragraph(draw, (x + 34, 574), footer, 470, 20, color=MUTED, bold=True)
        x += 614
    draw.rounded_rectangle((72, 778, 1848, 938), radius=8, fill="#0f151d", outline="#4a3824", width=2)
    text(draw, (112, 816), "FAIL-CLOSED RULE", 20, color=AMBER, bold=True)
    paragraph(draw, (112, 858), "Unsupported authority cannot be created by editing and resealing the same receipt.", 1660, 32, color=TEXT)
    built.append(save_slide("03_separation.png", canvas))

    canvas, draw = base_slide("Guided authority attack", "Valid receipt. Requested PROMOTE. Effective HOLD.", RED, 3)
    paste_panel(canvas, crop_top(required_sources["authority_attack"], 660), (72, 154, 1160, 874))
    draw.rounded_rectangle((1200, 154, 1848, 846), radius=8, fill="#0f151d", outline="#3a4654", width=2)
    text(draw, (1232, 190), "VERIFICATION LOG", 20, color=RED, bold=True)
    text(draw, (1232, 250), "receipt PASS", 30, color=GREEN, bold=True, mono=True)
    text(draw, (1232, 294), "requested PROMOTE", 26, color=RED, bold=True, mono=True)
    paragraph(draw, (1232, 346), "Self-authored PASS values cannot mint engineering, safety, or human authority.", 552, 26, color=TEXT)
    text(draw, (1232, 528), "REQUIRED GATES", 18, color=MUTED, bold=True)
    text(draw, (1232, 566), "4 held", 28, color=AMBER, bold=True)
    text(draw, (1232, 658), "EFFECTIVE DECISION", 18, color=MUTED, bold=True)
    text(draw, (1232, 696), "HOLD", 30, color=AMBER, bold=True)
    text(draw, (72, 924), "Policy blocks authority escalation even when the resealed receipt remains hash-valid.", 28, color=MUTED)
    built.append(save_slide("04_authority_attack.png", canvas))

    canvas, draw = base_slide("Exact restoration", "Canonical text and HOLD state return byte-for-byte.", GREEN, 4)
    paste_panel(canvas, crop_top(required_sources["restored"], 660), (72, 154, 1848, 874))
    draw.rounded_rectangle((72, 916, 630, 1004), radius=8, fill=PANEL, outline=GREEN, width=2)
    draw.rounded_rectangle((680, 916, 1238, 1004), radius=8, fill=PANEL, outline=GREEN, width=2)
    draw.rounded_rectangle((1288, 916, 1848, 1004), radius=8, fill=PANEL, outline=AMBER, width=2)
    text(draw, (104, 944), "Canonical receipt restored", 24, color=GREEN, bold=True)
    text(draw, (712, 944), "Artifacts reverified 4 / 4", 24, color=GREEN, bold=True)
    text(draw, (1320, 944), "Effective decision HOLD", 24, color=AMBER, bold=True)
    built.append(save_slide("05_restored.png", canvas))

    canvas, draw = base_slide("Reproducibility", "Browser and Python enforce the same policy.", GREEN, 5)
    checks = (
        ("BROWSER", "Same-origin artifact hashing and effective-gate derivation", BLUE),
        ("PYTHON", "Independent command-line receipt verifier", GREEN),
        ("TESTS", test_evidence, GREEN),
        ("RELEASE", "Dedicated 15-file deployment path; live release remains gated", AMBER),
    )
    y = 180
    for label, body, color in checks:
        draw.rounded_rectangle((72, y, 1848, y + 150), radius=8, fill=PANEL, outline=color, width=2)
        text(draw, (110, y + 30), label, 20, color=color, bold=True)
        paragraph(draw, (360, y + 28), body, 1420, 28, color=TEXT)
        y += 178
    text(draw, (72, 916), "SOURCE COMMIT", 18, color=MUTED, bold=True)
    text(draw, (284, 912), public_commit, 22, color=TEXT, mono=True)
    built.append(save_slide("06_reproducibility.png", canvas))

    canvas, draw = base_slide("Codex contribution", "Implementation, challenge, tests, and provenance.", BLUE, 6)
    roles = (
        ("ISOLATE", "Bound the release from unrelated repository history.", BLUE),
        ("IMPLEMENT", "Keep browser and Python verification behavior aligned.", GREEN),
        ("CHALLENGE", "Attempt a validly resealed authority escalation.", RED),
        ("VERIFY", "Preserve exact restoration, hashes, and claim limits.", AMBER),
    )
    y = 180
    for verb, body, color in roles:
        draw.rounded_rectangle((72, y, 1848, y + 150), radius=8, fill=PANEL, outline=color, width=2)
        text(draw, (110, y + 30), verb, 20, color=color, bold=True)
        paragraph(draw, (360, y + 28), body, 1420, 28, color=TEXT)
        y += 178
    draw.rounded_rectangle((72, 916, 1848, 1004), radius=8, fill="#0f151d", outline=AMBER, width=2)
    text(draw, (110, 942), "HUMAN AUTHORITY IS NOT DELEGATED TO THE BUILD SYSTEM", 24, color=AMBER, bold=True)
    built.append(save_slide("07_codex_boundary.png", canvas))

    canvas, draw = base_slide("ProofLock Console", "Evidence before claims.", GREEN, 7)
    text(draw, (72, 226), "PUBLIC REPOSITORY", 20, color=GREEN, bold=True)
    paragraph(draw, (72, 270), "github.com/robertashworth1986-debug/lumen-core-public", 1050, 30, color=TEXT)
    text(draw, (72, 382), "PUBLIC RELEASE GATE", 20, color=AMBER, bold=True)
    paragraph(draw, (72, 426), "Final publication waits for exact 15 / 15 live byte identity.", 1050, 30, color=TEXT)
    draw_corona_mark(canvas, (1544, 350), 190)
    draw.rounded_rectangle((72, 610, 1848, 778), radius=8, fill=PANEL, outline="#344252", width=2)
    paragraph(
        draw,
        (112, 650),
        "ProofLock verifies integrity and gate logic. It does not claim external validation, safety certification, patent rights, funding, or commercial readiness.",
        1680,
        30,
        color=MUTED,
    )
    text(draw, (72, 930), "Computer-generated narration.", 22, color=MUTED)
    built.append(save_slide("08_close.png", canvas))

    return built


def narration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def write_concat(slides: Iterable[Path], durations: Iterable[float]) -> None:
    rows: list[str] = []
    slide_list = list(slides)
    duration_list = list(durations)
    for slide, duration in zip(slide_list, duration_list, strict=True):
        rows.append(f"file '{slide.as_posix()}'")
        rows.append(f"duration {duration:.3f}")
    rows.append(f"file '{slide_list[-1].as_posix()}'")
    CONCAT_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("imageio-ffmpeg is required to build the demo video") from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def render_motion_segments(slides: list[Path], durations: list[float]) -> list[Path]:
    SEGMENT_DIR.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    for index, (slide, duration) in enumerate(zip(slides, durations, strict=True), start=1):
        horizontal_phase = (index - 1) * 0.7
        vertical_phase = (index - 1) * 0.5
        segment = SEGMENT_DIR / f"{index:02d}_{slide.stem}.mp4"
        motion_filter = (
            "fps=30,"
            "scale=1948:1096:flags=lanczos,"
            f"crop={WIDTH}:{HEIGHT}:"
            f"x='(in_w-out_w)/2+4*sin(t*0.31+{horizontal_phase:.2f})':"
            f"y='(in_h-out_h)/2+3*cos(t*0.27+{vertical_phase:.2f})',"
            "setsar=1,format=yuv420p"
        )
        subprocess.run(
            [
                ffmpeg_executable(),
                "-y",
                "-loglevel",
                "warning",
                "-loop",
                "1",
                "-framerate",
                "30",
                "-t",
                f"{duration:.3f}",
                "-i",
                str(slide),
                "-vf",
                motion_filter,
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "16",
                "-r",
                "30",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(segment),
            ],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [ffmpeg_executable(), "-v", "error", "-i", str(segment), "-f", "null", "-"],
            cwd=ROOT,
            check=True,
        )
        segments.append(segment)
    return segments


def build_video(slides: list[Path]) -> None:
    if not NARRATION_PATH.is_file():
        raise FileNotFoundError(f"missing narration: {NARRATION_PATH}")
    durations = [duration for _, duration in SLIDE_SPECS]
    audio_seconds = narration_seconds(NARRATION_PATH)
    durations[-1] += audio_seconds - sum(durations)
    if durations[-1] < 1.0:
        raise RuntimeError("slide timing exceeds narration duration")
    write_concat(slides, durations)
    transition_seconds = 0.45
    input_durations = [
        duration + (transition_seconds if index < len(durations) - 1 else 0.0)
        for index, duration in enumerate(durations)
    ]
    segments = render_motion_segments(slides, input_durations)
    command = [ffmpeg_executable(), "-y", "-loglevel", "warning"]
    for segment in segments:
        command.extend(["-i", str(segment)])
    command.extend(["-i", str(NARRATION_PATH)])

    filters: list[str] = []
    transitions = ("fade", "fade", "fadeblack", "smoothleft", "fade", "smoothup", "fadeblack")
    current_label = "0:v"
    elapsed = input_durations[0]
    for index in range(1, len(slides)):
        output_label = f"x{index}"
        offset = elapsed - transition_seconds
        filters.append(
            f"[{current_label}][{index}:v]"
            f"xfade=transition={transitions[index - 1]}:duration={transition_seconds:.3f}:"
            f"offset={offset:.3f}[{output_label}]"
        )
        current_label = output_label
        elapsed += input_durations[index] - transition_seconds

    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            f"[{current_label}]",
            "-map",
            f"{len(segments)}:a:0",
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-t",
            f"{audio_seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "17",
            "-r",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(OUTPUT_PATH),
        ]
    )
    subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run(
        [ffmpeg_executable(), "-v", "error", "-i", str(OUTPUT_PATH), "-f", "null", "-"],
        cwd=ROOT,
        check=True,
    )


def write_receipt(
    observed_utc: str,
    slides: list[Path],
    public_commit: str,
    test_evidence: str,
) -> Path:
    audio_seconds = narration_seconds(NARRATION_PATH)
    if not (1.0 < audio_seconds < 180.0):
        raise RuntimeError("narration duration is outside the Build Week video limit")
    facts = {
        "schema": "lumencore.prooflock_build_week_demo_video_receipt.v1",
        "observed_utc": observed_utc,
        "video": {
            "path": OUTPUT_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(OUTPUT_PATH),
            "size_bytes": OUTPUT_PATH.stat().st_size,
            "container": "mp4",
            "video_codec": "h264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "width": WIDTH,
            "height": HEIGHT,
        },
        "thumbnail": {
            "path": THUMBNAIL_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(THUMBNAIL_PATH),
            "size_bytes": THUMBNAIL_PATH.stat().st_size,
            "width": Image.open(THUMBNAIL_PATH).width,
            "height": Image.open(THUMBNAIL_PATH).height,
            "aspect_ratio": "3:2",
        },
        "narration": {
            "path": NARRATION_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(NARRATION_PATH),
            "duration_seconds": round(audio_seconds, 3),
            "generation_class": "LOCAL_WINDOWS_SYNTHETIC_SPEECH_MICROSOFT_MARK",
            "openai_audio_api_succeeded": False,
            "voice_disclosure": "Computer-generated narration.",
        },
        "source_frames": [
            {
                "path": source.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(source),
                "width": Image.open(source).width,
                "height": Image.open(source).height,
            }
            for source in sorted(SOURCE_DIR.glob("*.png"))
        ],
        "slides": [
            {
                "path": slide.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(slide),
                "width": Image.open(slide).width,
                "height": Image.open(slide).height,
            }
            for slide in slides
        ],
        "motion_segments": [
            {
                "path": segment.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(segment),
                "size_bytes": segment.stat().st_size,
            }
            for segment in (
                SEGMENT_DIR / f"{index:02d}_{slide.stem}.mp4"
                for index, slide in enumerate(slides, start=1)
            )
        ],
        "public_console_commit": public_commit,
        "focused_test_evidence": test_evidence,
        "motion_design": {
            "frames_per_second": 30,
            "maximum_zoom": 1.015,
            "crossfade_seconds": 0.45,
            "transition_classes": [
                "fade",
                "fade",
                "fadeblack",
                "smoothleft",
                "fade",
                "smoothup",
                "fadeblack",
            ],
            "audio_bed": "NONE",
            "audio_normalization": "EBU_R128_SINGLE_PASS_I_-16_TP_-1.5_LRA_11",
        },
        "claim_boundary": (
            "This receipt proves local demo-video assembly, declared input identities, bounded duration, and a "
            "successful decode check. It does not prove YouTube publication, Devpost acceptance, judging, award, "
            "OpenAI endorsement, external validation, safety, patent rights, funding, or commercial readiness."
        ),
    }
    receipt = {**facts, "facts_sha256": stable_hash(facts)}
    receipt["receipt_sha256"] = stable_hash(receipt)
    temporary = RECEIPT_PATH.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, RECEIPT_PATH)
    return RECEIPT_PATH


def normalize_utc(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _resolve_receipt_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")) or ":" in value:
        return None
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate


def verify_video_receipt(receipt: object) -> tuple[bool, list[str]]:
    if not isinstance(receipt, dict):
        return False, ["receipt_not_object"]
    errors: list[str] = []
    if receipt.get("schema") != "lumencore.prooflock_build_week_demo_video_receipt.v1":
        errors.append("schema_mismatch")

    unhashed = copy.deepcopy(receipt)
    recorded_receipt_hash = unhashed.pop("receipt_sha256", None)
    if recorded_receipt_hash != stable_hash(unhashed):
        errors.append("receipt_hash_mismatch")
    facts = copy.deepcopy(unhashed)
    recorded_facts_hash = facts.pop("facts_sha256", None)
    if recorded_facts_hash != stable_hash(facts):
        errors.append("facts_hash_mismatch")

    duration = receipt.get("narration", {}).get("duration_seconds")
    if not isinstance(duration, (int, float)) or not 1 < duration < 180:
        errors.append("duration_out_of_bounds")
    if receipt.get("motion_design", {}).get("audio_bed") != "NONE":
        errors.append("unexpected_audio_bed")
    if receipt.get("motion_design", {}).get("audio_normalization") != (
        "EBU_R128_SINGLE_PASS_I_-16_TP_-1.5_LRA_11"
    ):
        errors.append("audio_normalization_mismatch")
    narration = receipt.get("narration", {})
    if narration.get("openai_audio_api_succeeded") is not False:
        errors.append("narration_api_status_invalid")
    if narration.get("voice_disclosure") != "Computer-generated narration.":
        errors.append("narration_disclosure_missing")

    entries: list[tuple[str, dict[str, object]]] = []
    for label in ("video", "thumbnail", "narration"):
        entry = receipt.get(label)
        if isinstance(entry, dict):
            entries.append((label, entry))
        else:
            errors.append(f"{label}_entry_missing")
    for label in ("source_frames", "slides", "motion_segments"):
        rows = receipt.get(label)
        if not isinstance(rows, list) or not rows:
            errors.append(f"{label}_missing")
            continue
        for index, row in enumerate(rows):
            if isinstance(row, dict):
                entries.append((f"{label}_{index}", row))
            else:
                errors.append(f"{label}_{index}_invalid")

    for label, entry in entries:
        path = _resolve_receipt_path(entry.get("path"))
        if path is None:
            errors.append(f"{label}_unsafe_path")
            continue
        if not path.is_file():
            errors.append(f"{label}_missing_file")
            continue
        if entry.get("sha256") != sha256_file(path):
            errors.append(f"{label}_hash_mismatch")
        recorded_size = entry.get("size_bytes")
        if isinstance(recorded_size, int) and recorded_size != path.stat().st_size:
            errors.append(f"{label}_size_mismatch")

    if len(receipt.get("slides", [])) != 8:
        errors.append("slide_count_mismatch")
    if len(receipt.get("source_frames", [])) != 3:
        errors.append("source_frame_count_mismatch")
    if len(receipt.get("motion_segments", [])) != 8:
        errors.append("segment_count_mismatch")
    thumbnail = receipt.get("thumbnail", {})
    if thumbnail.get("width") != 1500 or thumbnail.get("height") != 1000:
        errors.append("thumbnail_dimensions_mismatch")
    if thumbnail.get("aspect_ratio") != "3:2":
        errors.append("thumbnail_aspect_ratio_mismatch")
    commit = receipt.get("public_console_commit")
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        errors.append("public_commit_invalid")
    test_evidence = receipt.get("focused_test_evidence")
    if not isinstance(test_evidence, str) or not test_evidence.strip():
        errors.append("focused_test_evidence_missing")
    return not errors, sorted(set(errors))


def verify_video_receipt_file(path: Path = RECEIPT_PATH) -> tuple[bool, list[str]]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ["receipt_file_unreadable"]
    return verify_video_receipt(receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the bounded ProofLock Build Week demo video.")
    parser.add_argument("--observed-utc")
    parser.add_argument("--public-commit", help="Exact 40-character source commit used for the recording.")
    parser.add_argument("--test-evidence", help="Exact focused local test result used for the recording.")
    parser.add_argument("--verify", action="store_true", help="Verify the existing video receipt and inputs.")
    args = parser.parse_args()
    if args.verify:
        valid, errors = verify_video_receipt_file()
        print(json.dumps({"valid": valid, "errors": errors}, indent=2))
        return 0 if valid else 1
    if not args.observed_utc:
        parser.error("--observed-utc is required when building")
    if not args.public_commit or re.fullmatch(r"[0-9a-f]{40}", args.public_commit) is None:
        parser.error("--public-commit must be an exact lowercase 40-character commit")
    if not args.test_evidence or not args.test_evidence.strip():
        parser.error("--test-evidence is required when building")
    observed_utc = normalize_utc(args.observed_utc)
    slides = build_slides(args.public_commit, args.test_evidence.strip())
    build_thumbnail()
    build_video(slides)
    receipt = write_receipt(
        observed_utc,
        slides,
        args.public_commit,
        args.test_evidence.strip(),
    )
    valid, errors = verify_video_receipt_file(receipt)
    if not valid:
        raise RuntimeError("video receipt verification failed: " + "; ".join(errors))
    print(
        json.dumps(
            {
                "video": OUTPUT_PATH.relative_to(ROOT).as_posix(),
                "video_sha256": sha256_file(OUTPUT_PATH),
                "thumbnail": THUMBNAIL_PATH.relative_to(ROOT).as_posix(),
                "thumbnail_sha256": sha256_file(THUMBNAIL_PATH),
                "narration_seconds": round(narration_seconds(NARRATION_PATH), 3),
                "receipt": receipt.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
