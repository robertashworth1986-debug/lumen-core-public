from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


APP_ROOT = Path(__file__).resolve().parents[1]
DOCS = APP_ROOT / "docs"

BG = "#07131f"
PANEL = "#10293a"
PANEL_ALT = "#183a4e"
CYAN = "#31f7e6"
VIOLET = "#b37aff"
WHITE = "#f3fbff"
MUTED = "#a7c1cf"
RED = "#ff6b7f"
GREEN = "#7ef29a"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


F_TITLE = font(42, True)
F_SUB = font(24)
F_BOX = font(25, True)
F_SMALL = font(19)
F_TINY = font(16)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str, width: int = 3) -> None:
    draw.rounded_rectangle(box, radius=22, fill=fill, outline=outline, width=width)


def centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], lines: list[str], title_color: str = WHITE) -> None:
    x1, y1, x2, y2 = box
    heights = [draw.textbbox((0, 0), line, font=F_BOX if i == 0 else F_SMALL)[3] for i, line in enumerate(lines)]
    total = sum(heights) + 10 * (len(lines) - 1)
    y = y1 + (y2 - y1 - total) / 2
    for i, line in enumerate(lines):
        active_font = F_BOX if i == 0 else F_SMALL
        bbox = draw.textbbox((0, 0), line, font=active_font)
        x = x1 + (x2 - x1 - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), line, font=active_font, fill=title_color if i == 0 else MUTED)
        y += heights[i] + 10


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str = CYAN, width: int = 5) -> None:
    draw.line([start, end], fill=color, width=width)
    ex, ey = end
    sx, sy = start
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    size = 16
    p1 = (ex - ux * size + px * size * 0.6, ey - uy * size + py * size * 0.6)
    p2 = (ex - ux * size - px * size * 0.6, ey - uy * size - py * size * 0.6)
    draw.polygon([end, p1, p2], fill=color)


def interaction_diagram() -> None:
    image = Image.new("RGB", (1800, 1150), BG)
    draw = ImageDraw.Draw(image)
    draw.text((80, 52), "LumenCore Opportunity Decision Agent", font=F_TITLE, fill=WHITE)
    draw.text((80, 110), "Manager-owned synthesis · allowlisted read-only evidence · HumanUnlock always outside", font=F_SUB, fill=MUTED)

    source_box = (80, 250, 430, 620)
    manager_box = (670, 340, 1130, 590)
    output_box = (1370, 340, 1720, 590)
    rounded(draw, source_box, PANEL, CYAN)
    centered(draw, source_box, ["Deterministic tools", "Exact record_ref allowlist", "SHA-256 + freshness", "Public policy boundaries"])
    rounded(draw, manager_box, PANEL_ALT, VIOLET, 5)
    centered(draw, manager_box, ["Decision Manager", "Owns final structured brief", "Reconciles conservatively"])
    rounded(draw, output_box, PANEL, GREEN)
    centered(draw, output_box, ["Decision brief", "Observed / inferred / modeled", "BID · PARTNER · WATCH", "NO_BID · DRAFT_READY"])
    arrow(draw, (430, 435), (670, 435))
    arrow(draw, (1130, 435), (1370, 435))

    specialists = [
        ((530, 730, 830, 930), "Eligibility", "Applicant · deadline · route"),
        ((850, 730, 1150, 930), "Licensing / IP", "Rights · disclosure · terms"),
        ((1170, 730, 1470, 930), "Evidence / claims", "Receipts · maturity · limits"),
        ((1490, 730, 1770, 930), "Adversarial", "Try to falsify readiness"),
    ]
    for box, title, subtitle in specialists:
        rounded(draw, box, PANEL, VIOLET)
        centered(draw, box, [title, subtitle])
        arrow(draw, ((box[0] + box[2]) // 2, box[1]), (900, manager_box[3]), VIOLET, 3)

    gate_box = (80, 760, 430, 1010)
    rounded(draw, gate_box, "#3a1822", RED, 5)
    centered(draw, gate_box, ["HumanUnlock boundary", "Send · submit · terms · sign", "Spend · publish · private upload", "Account change", "Never granted by the brief"], RED)
    arrow(draw, (1370, 590), (430, 850), RED, 4)
    draw.text((80, 1070), "No browser · no shell · no arbitrary files · no email/portal/GitHub mutation · no pricing/signature/payment/trading/deploy tools", font=F_SMALL, fill=MUTED)
    DOCS.mkdir(parents=True, exist_ok=True)
    image.save(DOCS / "agent-interactions.png", optimize=True)


def sequence_diagram() -> None:
    image = Image.new("RGB", (1800, 1250), BG)
    draw = ImageDraw.Draw(image)
    draw.text((80, 52), "Fail-closed opportunity decision sequence", font=F_TITLE, fill=WHITE)
    draw.text((80, 110), "One turn; public-safe sources; deterministic post-validation; no external action", font=F_SUB, fill=MUTED)

    actors = [(150, "CLI"), (500, "Allowlist loader"), (850, "Manager"), (1200, "Specialists"), (1550, "Validator")]
    for x, label in actors:
        rounded(draw, (x - 130, 180, x + 130, 260), PANEL, CYAN)
        centered(draw, (x - 130, 180, x + 130, 260), [label])
        draw.line([(x, 260), (x, 1120)], fill="#416174", width=2)

    events = [
        (320, 150, 500, "record_ref + as_of + request", CYAN),
        (410, 500, 150, "exact record + hash/freshness", CYAN),
        (500, 150, 850, "bounded request", VIOLET),
        (590, 850, 1200, "4 distinct specialist calls", VIOLET),
        (680, 1200, 850, "eligibility · IP · claims · challenge", VIOLET),
        (770, 850, 1550, "structured brief", GREEN),
        (860, 1550, 500, "recheck exact source bytes and gates", GREEN),
        (950, 500, 1550, "canonical receipts", GREEN),
        (1040, 1550, 150, "validated brief or fail-closed error", GREEN),
    ]
    for y, start_x, end_x, label, color in events:
        arrow(draw, (start_x, y), (end_x, y), color, 4)
        bbox = draw.textbbox((0, 0), label, font=F_TINY)
        draw.rectangle((min(start_x, end_x) + 10, y - 29, min(start_x, end_x) + 20 + bbox[2], y - 5), fill=BG)
        draw.text((min(start_x, end_x) + 15, y - 28), label, font=F_TINY, fill=color)

    rounded(draw, (1150, 1125, 1740, 1210), "#3a1822", RED)
    centered(draw, (1150, 1125, 1740, 1210), ["External action remains locked", "Fresh exact HumanUnlock is a separate future event"], RED)
    DOCS.mkdir(parents=True, exist_ok=True)
    image.save(DOCS / "agent-sequence.png", optimize=True)


def main() -> int:
    interaction_diagram()
    sequence_diagram()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
