from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_STEM = "Robert_Ashworth_Infrastructure_AI_Evaluation_Resume"
LEGACY_HTML_NAME = "RESUME_LUMENCORE_ELITE.html"
LEGACY_PDF_NAME = "RESUME_LUMENCORE_ELITE.pdf"


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


def build_html(resume_md: Path, html_out: Path) -> Path:
    html_out.parent.mkdir(parents=True, exist_ok=True)
    md = resume_md.read_text(encoding="utf-8")
    body = markdown.markdown(md, extensions=["fenced_code", "tables", "sane_lists"])
    body = body.replace(
        "<h2>PROFESSIONAL EXPERIENCE</h2>",
        '<h2 class="page-break-before">PROFESSIONAL EXPERIENCE</h2>',
    )
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Robert Ashworth - Infrastructure and AI Evaluation Resume</title>
  <style>
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
      font-size: 14px;
      line-height: 1.34;
      padding: 24px;
    }}
    .page {{
      max-width: 900px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid var(--line);
      box-shadow: 0 6px 24px rgba(8, 21, 44, 0.08);
      padding: 30px 38px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      letter-spacing: 0.02em;
      color: var(--ink);
      border-bottom: 2px solid var(--accent);
      padding-bottom: 10px;
    }}
    h2 {{
      margin: 14px 0 6px;
      font-size: 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
      border-top: 1px solid var(--line);
      padding-top: 8px;
    }}
    h3 {{
      margin: 9px 0 4px;
      font-size: 14px;
      color: var(--ink);
    }}
    p {{ margin: 4px 0; color: var(--muted); }}
    ul {{ margin: 5px 0 5px 18px; color: var(--muted); }}
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
      @page {{ size: Letter; margin: 0.40in; }}
      body {{ background: #fff; padding: 0; }}
      .page {{ border: 0; box-shadow: none; padding: 0; max-width: none; }}
      h2, h3 {{ break-after: avoid; page-break-after: avoid; }}
      li {{ break-inside: avoid; page-break-inside: avoid; }}
      .page-break-before {{
        break-before: page;
        page-break-before: always;
        border-top: 0;
        margin-top: 0;
        padding-top: 0;
      }}
    }}
  </style>
</head>
<body>
  <div class=\"page\">{body}</div>
</body>
</html>
"""
    html_out.write_text(html, encoding="utf-8")
    return html_out


def build_pdf(html_path: Path, pdf_out: Path) -> bool:
    browser = _find_browser()
    if not browser:
        return False

    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={str(pdf_out)}",
        html_path.resolve().as_uri(),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=40)
        return pdf_out.exists() and pdf_out.stat().st_size > 0
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the evidence-bounded LumenCore resume as HTML and PDF."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.getenv("LUMA_STACK_ROOT") or DEFAULT_ROOT),
        help="Repository root. Defaults to the repository containing this script.",
    )
    parser.add_argument("--resume-md", type=Path, help="Optional resume Markdown path.")
    parser.add_argument("--output-dir", type=Path, help="Optional canonical output directory.")
    parser.add_argument(
        "--no-legacy-copy",
        action="store_true",
        help="Do not refresh compatibility copies under out/resume.",
    )
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    resume_md = (args.resume_md or (root / "RESUME_LUMENCORE.md")).expanduser().resolve()
    output_dir = (args.output_dir or (root / "output" / "pdf")).expanduser().resolve()
    html_out = output_dir / f"{CANONICAL_STEM}.html"
    pdf_out = output_dir / f"{CANONICAL_STEM}.pdf"

    if not resume_md.exists():
        print(f"Missing resume markdown: {resume_md}")
        return 1

    html = build_html(resume_md, html_out)
    ok = build_pdf(html, pdf_out)
    print(f"HTML_OUT={html}")
    if ok:
        print(f"PDF_OUT={pdf_out}")
        if not args.no_legacy_copy:
            legacy_dir = root / "out" / "resume"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            legacy_html = legacy_dir / LEGACY_HTML_NAME
            legacy_pdf = legacy_dir / LEGACY_PDF_NAME
            shutil.copy2(html, legacy_html)
            shutil.copy2(pdf_out, legacy_pdf)
            print(f"LEGACY_HTML_OUT={legacy_html}")
            print(f"LEGACY_PDF_OUT={legacy_pdf}")
        return 0
    print("PDF build failed. HTML was generated and can be printed to PDF manually.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
