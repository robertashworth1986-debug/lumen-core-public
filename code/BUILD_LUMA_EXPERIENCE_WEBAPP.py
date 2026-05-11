from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

STAMP_RE = re.compile(r"(Generated UTC:\s*)([^<]+)")


def _score_source(text: str) -> tuple[int, int]:
    score = 0
    if "CAN_TRY_LIVE_API" in text:
        score += 4
    if "resolveWsUrl" in text:
        score += 3
    if "loadLocalSnapshot" in text:
        score += 3
    if "WebSocket disabled in local artifact mode" in text:
        score += 2
    if "function bootScene()" in text:
        score += 1
    return score, len(text)


def _update_generated_stamp(html: str) -> str:
    stamp = datetime.now(timezone.utc).isoformat()
    return STAMP_RE.sub(lambda m: f"{m.group(1)}{stamp}", html, count=1)


def _load_best_source(candidates: list[Path]) -> tuple[Path, str]:
    best_path: Path | None = None
    best_text = ""
    best_score = (-1, -1)

    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        score = _score_source(text)
        if score > best_score:
            best_score = score
            best_path = path
            best_text = text

    if best_path is None:
        raise SystemExit("No immersive page source found in expected locations.")

    return best_path, best_text


def main() -> None:
    stack_root = Path(__file__).resolve().parent.parent
    workspace_root = stack_root.parent

    top_dash = workspace_root / "dashboard" / "luma_experience.html"
    stack_dash = stack_root / "dashboard" / "luma_experience.html"

    source, html = _load_best_source([top_dash, stack_dash])
    html = _update_generated_stamp(html)

    targets = [top_dash, stack_dash]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        print(str(target))

    print(f"[sync] source={source}")


if __name__ == "__main__":
    main()
