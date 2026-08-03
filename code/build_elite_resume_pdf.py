from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "resume"
RESUME_MD = ROOT / "RESUME_LUMENCORE.md"
HTML_OUT = OUT / "RESUME_LUMENCORE_ELITE.html"
PDF_OUT = OUT / "RESUME_LUMENCORE_ELITE.pdf"


def _find_browser() -> str | None:
    candidates = [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def build_html() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    md = RESUME_MD.read_text(encoding="utf-8")
    body = markdown.markdown(md, extensions=["fenced_code", "tables", "sane_lists"])
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Robert Ashworth - Resume</title>
  <style>
    @page {{
      size: Letter;
      margin: 0.45in 0.55in;
    }}
    :root {{
      --ink: #0f1c2f;
      --muted: #31445f;
      --accent: #0b5cad;
      --line: #d6dde8;
      --bg: #f3f7fb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", Tahoma, Arial, sans-serif;
      font-size: 12.5px;
      line-height: 1.28;
      padding: 24px;
    }}
    .page {{
      max-width: 900px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid var(--line);
      box-shadow: 0 6px 24px rgba(8, 21, 44, 0.08);
      padding: 28px 34px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 25px;
      letter-spacing: 0.02em;
      color: var(--ink);
      border-bottom: 2px solid var(--accent);
      padding-bottom: 10px;
    }}
    h2 {{
      margin: 13px 0 6px;
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
      border-top: 1px solid var(--line);
      padding-top: 7px;
      break-after: avoid-page;
      page-break-after: avoid;
    }}
    h3 {{
      margin: 9px 0 4px;
      font-size: 13px;
      color: var(--ink);
      break-after: avoid-page;
      page-break-after: avoid;
    }}
    p {{ margin: 4px 0; color: var(--muted); }}
    ul {{ margin: 5px 0 6px 18px; color: var(--muted); }}
    li {{ margin: 3px 0; }}
    code {{
      background: #eef3f9;
      border: 1px solid #d8e1ed;
      border-radius: 4px;
      padding: 0 5px;
      color: #1d3555;
      font-family: Consolas, monospace;
    }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .page {{ border: 0; box-shadow: none; padding: 0; max-width: none; }}
    }}
  </style>
</head>
<body>
  <div class=\"page\">{body}</div>
</body>
</html>
"""
    HTML_OUT.write_text(html, encoding="utf-8")
    return HTML_OUT


def build_pdf(html_path: Path) -> bool:
    browser = _find_browser()
    if not browser:
        return False

    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={str(PDF_OUT)}",
        html_path.resolve().as_uri(),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=40)
        return PDF_OUT.exists()
    except Exception:
        return False


def main() -> int:
    if not RESUME_MD.exists():
        print(f"Missing resume markdown: {RESUME_MD}")
        return 1

    html = build_html()
    ok = build_pdf(html)
    print(f"HTML_OUT={html}")
    if ok:
        print(f"PDF_OUT={PDF_OUT}")
        return 0
    print("PDF build failed. HTML was generated and can be printed to PDF manually.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
