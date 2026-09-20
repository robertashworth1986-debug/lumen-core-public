from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import logging
import os
import re
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from PIL import Image, UnidentifiedImageError
except Exception:
    Image = None
    UnidentifiedImageError = Exception


DOC_EXTS = {
    ".pdf",
    ".txt",
    ".md",
    ".rtf",
    ".html",
    ".htm",
    ".docx",
    ".pptx",
    ".json",
    ".csv",
}

IMG_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".svg",
}

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "venv3.11",
    "env",
    "env311",
    "site-packages",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "$recycle.bin",
    "system volume information",
    "recovery",
    "perflogs",
    "msocache",
}

SKIP_PATH_TOKENS = (
    "\\site-packages\\",
    "\\node_modules\\",
    "\\__pycache__\\",
    "\\.venv\\",
    "\\venv\\",
    "\\venv3.11\\",
    "\\env311\\",
    "\\.git\\",
    "\\windows\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\programdata\\",
    "\\$recycle.bin\\",
    "\\system volume information\\",
    "\\appdata\\local\\packages\\",
    "\\appdata\\local\\microsoft\\edge\\",
    "\\appdata\\local\\microsoft\\olk\\",
    "\\appdata\\local\\temp\\",
    "\\appdata\\locallow\\",
    "\\cache\\cache_data\\",
    "\\code cache\\",
    "\\service worker\\",
)

KEYWORD_GROUPS = {
    "robot": [
        "robot",
        "robotic",
        "robotics",
        "autonomous",
        "humanoid",
        "mechatronic",
        "actuator",
        "exo",
        "drone",
        "machine body",
    ],
    "proof": [
        "proof",
        "evidence",
        "audit",
        "sha256",
        "chain_of_custody",
        "chain-of-custody",
        "ledger",
        "txid",
        "verification",
        "readiness",
        "institutional",
    ],
    "plot": [
        "plot",
        "chart",
        "figure",
        "graph",
        "timeseries",
        "time series",
        "rmse",
        "holdout",
        "coherence",
        "heatmap",
        "backtest",
        "signal",
    ],
    "luma": [
        "luma",
        "lumencore",
        "flowform",
        "echolock",
        "whitehole",
        "trinity",
        "kalisha",
        "sacred",
    ],
    "hardware": [
        "motherboard",
        "curved motherboard",
        "curved pcb",
        "honeycomb",
        "battery",
        "haptic",
        "spiral",
        "cymatic",
    ],
}

GROUP_WEIGHTS = {
    "robot": 5.0,
    "proof": 4.0,
    "plot": 4.0,
    "luma": 2.0,
    "hardware": 3.0,
}

PLOT_NAME_HINTS = (
    "plot",
    "chart",
    "figure",
    "rmse",
    "holdout",
    "coherence",
    "heatmap",
    "top10",
    "signal",
)

TERM_PATTERNS: dict[str, re.Pattern[str] | None] = {}
for _group_terms in KEYWORD_GROUPS.values():
    for _t in _group_terms:
        _k = _t.lower()
        if _k in TERM_PATTERNS:
            continue
        if " " in _k or "-" in _k or "_" in _k:
            TERM_PATTERNS[_k] = None
        else:
            TERM_PATTERNS[_k] = re.compile(rf"\b{re.escape(_k)}\b")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_from_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def clean_excerpt(text: str, max_len: int = 320) -> str:
    flat = re.sub(r"\s+", " ", text or "").strip()
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 3] + "..."


def decode_bytes(blob: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return blob.decode(enc, errors="replace")
        except Exception:
            continue
    return blob.decode("utf-8", errors="replace")


def is_skipped_dir(path_str_lower: str) -> bool:
    for token in SKIP_PATH_TOKENS:
        if token in path_str_lower:
            return True
    return False


def iter_user_files(root: Path, max_files: int):
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        path_lower = str(Path(dirpath)).lower()
        if is_skipped_dir(path_lower):
            dirnames[:] = []
            continue

        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in SKIP_DIR_NAMES and not d.startswith(".")
        ]

        for name in filenames:
            p = Path(dirpath) / name
            scanned += 1
            yield scanned, p
            if max_files > 0 and scanned >= max_files:
                return


def count_term(text_lower: str, term: str) -> int:
    t = term.lower()
    pat = TERM_PATTERNS.get(t)
    if pat is None:
        return text_lower.count(t)
    return len(pat.findall(text_lower))


def keyword_hits(path: Path, text_sample: str) -> tuple[dict[str, int], list[str]]:
    blob = (str(path) + "\n" + (text_sample or "")).lower()
    hits: dict[str, int] = {k: 0 for k in KEYWORD_GROUPS}
    matched_terms: list[str] = []
    for group, terms in KEYWORD_GROUPS.items():
        for term in terms:
            if term.lower() not in blob:
                continue
            c = count_term(blob, term)
            if c > 0:
                hits[group] += c
                matched_terms.append(term)
    dedup_terms = sorted(set(matched_terms))
    return hits, dedup_terms


def score_asset(
    hits: dict[str, int],
    age_days: float,
    has_embedded_images: bool,
    width: int,
    height: int,
    filename: str,
) -> float:
    base = 0.0
    for group, count in hits.items():
        base += float(count) * GROUP_WEIGHTS.get(group, 1.0)

    fresh_bonus = max(0.0, 3.0 - (age_days / 60.0))
    image_bonus = 2.0 if has_embedded_images else 0.0
    resolution_bonus = min(4.0, (float(width) * float(height)) / 1_000_000.0)
    name_bonus = 2.0 if any(h in filename.lower() for h in PLOT_NAME_HINTS) else 0.0
    return round(base + fresh_bonus + image_bonus + resolution_bonus + name_bonus, 3)


class _PdfDiagnostics(logging.Handler):
    """Bound retained messages while preserving the total diagnostic count."""
    def __init__(self):
        super().__init__(logging.WARNING)
        self.count = 0
        self.entries: list[dict[str, Any]] = []
        self.stage = "reader"
        self.page: int | None = None

    def add(self, category: str, message: str) -> None:
        self.count += 1
        if len(self.entries) < 50:
            self.entries.append({"stage": self.stage, "page": self.page,
                                 "category": category, "message": str(message)[:512]})

    def emit(self, record: logging.LogRecord) -> None:
        self.add(record.name, record.getMessage())


@contextmanager
def _capture_pdf_diagnostics(diagnostics: _PdfDiagnostics):
    # This is a sequential CLI collector. Restore host logging/filter state;
    # importing it must not suppress diagnostics in other PDF consumers.
    logger = logging.getLogger("pypdf")
    level, handlers, propagate, disabled = logger.level, logger.handlers[:], logger.propagate, logger.disabled
    logger.setLevel(logging.WARNING)
    logger.handlers = [diagnostics]
    logger.propagate = False
    logger.disabled = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            warnings.showwarning = lambda message, category, *a, **k: diagnostics.add(category.__name__, str(message))
            yield
    finally:
        logger.setLevel(level)
        logger.handlers = handlers
        logger.propagate, logger.disabled = propagate, disabled


def parse_pdf(path: Path, max_pages: int, max_chars: int, max_bytes: int = 2_500_000) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False, "error": "", "text": "", "pages_total": 0,
        "image_objects": 0, "pages_with_images": 0, "pages_inspected": 0,
        "pages_text_extracted": 0, "pages_without_text": 0,
        "inspection_status": "FAILED", "text_layer_complete": False,
        "image_inventory_complete": False, "ocr_performed": False,
        "source_sha256": "", "limits_reached": [], "diagnostics": [],
        "diagnostic_count": 0,
        "scope_boundary": "PDF text-layer and image-object discovery only. No OCR, visual review, scientific validation, or complete document understanding. Input bytes, selected pages and retained text are bounded; parser CPU and decompressed memory are not sandboxed.",
    }
    for name, value in (("max_pages", max_pages), ("max_chars", max_chars), ("max_bytes", max_bytes)):
        if type(value) is not int or value < 1:
            result["error"] = f"invalid_{name}"
            return result
    if PdfReader is None:
        result["error"] = "pypdf_not_installed"
        return result

    diagnostics = _PdfDiagnostics()
    text_failed = image_failed = False
    try:
        # A single bounded snapshot binds the inspected bytes. File metadata is
        # not sufficient when an export changes while discovery is running.
        with path.open("rb") as handle:
            blob = handle.read(max_bytes + 1)
        if len(blob) > max_bytes:
            result["error"] = "pdf_byte_limit_exceeded"
            result["limits_reached"].append("byte_limit")
            return result
        if not blob.startswith(b"%PDF-"):
            result["error"] = "invalid_pdf_header"
            return result
        result["source_sha256"] = hashlib.sha256(blob).hexdigest()
        with _capture_pdf_diagnostics(diagnostics):
            reader = PdfReader(BytesIO(blob), strict=False)
            result["pages_total"] = len(reader.pages)
            selected = min(result["pages_total"], max_pages)
            if selected < result["pages_total"]:
                result["limits_reached"].append("page_limit")
            for index in range(selected):
                diagnostics.stage, diagnostics.page = "page", index + 1
                page = reader.pages[index]
                result["pages_inspected"] += 1
                diagnostics.stage = "images"
                try:
                    count = len(getattr(page, "images", []))
                    result["image_objects"] += count
                    result["pages_with_images"] += int(count > 0)
                except Exception as exc:
                    image_failed = True
                    diagnostics.add(type(exc).__name__, str(exc))

                remaining = max_chars - len(result["text"])
                if remaining <= 0:
                    if "character_limit" not in result["limits_reached"]:
                        result["limits_reached"].append("character_limit")
                    continue
                diagnostics.stage = "text"
                try:
                    text = page.extract_text() or ""
                    if not isinstance(text, str):
                        raise TypeError("PDF text extractor returned non-text")
                    result["pages_text_extracted"] += 1
                    result["pages_without_text"] += int(not text.strip())
                    if text:
                        chunk = ("\n" if result["text"] else "") + text
                        if len(chunk) > remaining and "character_limit" not in result["limits_reached"]:
                            result["limits_reached"].append("character_limit")
                        result["text"] += chunk[:remaining]
                except Exception as exc:
                    text_failed = True
                    diagnostics.add(type(exc).__name__, str(exc))
        result["ok"] = True
    except Exception as exc:
        result["error"] = f"pdf_inspection_failed:{type(exc).__name__}"
        diagnostics.add(type(exc).__name__, str(exc))
    finally:
        result["diagnostics"] = diagnostics.entries
        result["diagnostic_count"] = diagnostics.count

    all_pages = result["pages_inspected"] == result["pages_total"]
    result["text_layer_complete"] = bool(result["ok"] and all_pages and not text_failed
        and not diagnostics.count and not result["limits_reached"]
        and result["pages_text_extracted"] == result["pages_total"])
    result["image_inventory_complete"] = bool(result["ok"] and all_pages and not image_failed and not diagnostics.count)
    if result["ok"]:
        complete = result["text_layer_complete"] and result["image_inventory_complete"]
        result["inspection_status"] = "TEXT_LAYER_INSPECTED" if complete else "PARTIAL"
    return result


def parse_docx(path: Path, max_chars: int) -> str:
    with ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.startswith("word/") and n.endswith(".xml")]
        text_parts: list[str] = []
        remaining = max_chars
        for name in names:
            if remaining <= 0:
                break
            blob = zf.read(name)
            matches = re.findall(rb"<w:t[^>]*>(.*?)</w:t>", blob, flags=re.DOTALL)
            for m in matches:
                if remaining <= 0:
                    break
                chunk = html.unescape(decode_bytes(m))
                if chunk:
                    chunk = chunk[:remaining]
                    text_parts.append(chunk)
                    remaining -= len(chunk)
        return "\n".join(text_parts)


def parse_pptx(path: Path, max_chars: int) -> str:
    with ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.startswith("ppt/slides/") and n.endswith(".xml")]
        names = sorted(names)
        text_parts: list[str] = []
        remaining = max_chars
        for name in names:
            if remaining <= 0:
                break
            blob = zf.read(name)
            matches = re.findall(rb"<a:t>(.*?)</a:t>", blob, flags=re.DOTALL)
            for m in matches:
                if remaining <= 0:
                    break
                chunk = html.unescape(decode_bytes(m))
                if chunk:
                    chunk = chunk[:remaining]
                    text_parts.append(chunk)
                    remaining -= len(chunk)
        return "\n".join(text_parts)


def parse_rtf(path: Path, max_bytes: int, max_chars: int) -> str:
    blob = path.read_bytes()[:max_bytes]
    text = decode_bytes(blob)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def parse_html(path: Path, max_bytes: int, max_chars: int) -> str:
    blob = path.read_bytes()[:max_bytes]
    text = decode_bytes(blob)
    text = re.sub(r"<script[\\s\\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\\s\\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def parse_text_like(path: Path, max_bytes: int, max_chars: int) -> str:
    blob = path.read_bytes()[:max_bytes]
    return decode_bytes(blob)[:max_chars]


def parse_document(path: Path, max_bytes: int, max_pages: int, max_chars: int) -> dict[str, Any]:
    ext = path.suffix.lower()
    out: dict[str, Any] = {
        "ok": True,
        "error": "",
        "text": "",
        "pages_total": 0,
        "image_objects": 0,
        "pages_with_images": 0,
    }

    try:
        if ext == ".pdf":
            return parse_pdf(path, max_pages=max_pages, max_chars=max_chars, max_bytes=max_bytes)
        if ext == ".docx":
            out["text"] = parse_docx(path, max_chars=max_chars)
            return out
        if ext == ".pptx":
            out["text"] = parse_pptx(path, max_chars=max_chars)
            return out
        if ext == ".rtf":
            out["text"] = parse_rtf(path, max_bytes=max_bytes, max_chars=max_chars)
            return out
        if ext in {".html", ".htm"}:
            out["text"] = parse_html(path, max_bytes=max_bytes, max_chars=max_chars)
            return out

        out["text"] = parse_text_like(path, max_bytes=max_bytes, max_chars=max_chars)
        return out
    except Exception as exc:
        out["ok"] = False
        out["error"] = str(exc)
        out["text"] = ""
        return out


def inspect_image(path: Path) -> dict[str, Any]:
    if Image is None:
        return {
            "ok": False,
            "error": "pillow_not_installed",
            "width": 0,
            "height": 0,
            "mode": "",
        }

    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            width, height = img.size
            mode = str(img.mode)
        return {
            "ok": True,
            "error": "",
            "width": int(width),
            "height": int(height),
            "mode": mode,
        }
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "width": 0,
            "height": 0,
            "mode": "",
        }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def safe_name(name: str, max_len: int = 64) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return s[:max_len].strip("_") or "asset"


def extract_pdf_previews(
    top_docs: list[dict[str, Any]],
    preview_dir: Path,
    max_docs: int,
    max_images_per_doc: int,
    max_bytes: int = 2_500_000,
    max_pages: int = 8,
    reports: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    preview_rows: list[dict[str, Any]] = []
    if type(max_bytes) is not int or max_bytes < 1 or type(max_pages) is not int or max_pages < 1:
        raise ValueError("Preview byte and page limits must be positive integers")
    if PdfReader is None or max_docs <= 0 or max_images_per_doc <= 0:
        return preview_rows

    preview_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    for doc in top_docs:
        if processed >= max_docs:
            break
        p = Path(str(doc.get("path", "")))
        if p.suffix.lower() != ".pdf":
            continue
        processed += 1
        report = {"source_pdf": str(p), "status": "FAILED", "images_extracted": 0,
                  "pages_inspected": 0, "diagnostic_count": 0, "diagnostics": []}
        if reports is not None:
            reports.append(report)
        diagnostics = _PdfDiagnostics()
        try:
            with p.open("rb") as fh:
                blob = fh.read(max_bytes + 1)
            if len(blob) > max_bytes:
                report["status"] = "BYTE_LIMIT_HOLD"
                continue
            digest = hashlib.sha256(blob).hexdigest()
            if not doc.get("source_sha256") or doc["source_sha256"] != digest:
                report["status"] = "SOURCE_IDENTITY_HOLD"
                continue
            report["source_sha256"] = digest
            with _capture_pdf_diagnostics(diagnostics):
                reader = PdfReader(BytesIO(blob), strict=False)
                taken = 0
                images_inspected = 0
                stem = safe_name(p.stem)
                selected = min(len(reader.pages), max_pages, int(doc.get("pages_inspected", 0)))
                for page_index in range(selected):
                    if images_inspected >= max_images_per_doc:
                        break
                    report["pages_inspected"] += 1
                    diagnostics.stage, diagnostics.page = "preview", page_index + 1
                    page = reader.pages[page_index]
                    for img_index, img in enumerate(getattr(page, "images", []), start=1):
                        if images_inspected >= max_images_per_doc:
                            break
                        images_inspected += 1
                        ext = img.name.rsplit(".", 1)[-1].lower() if "." in img.name else "bin"
                        if ext not in {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff", "jp2", "jpx"}:
                            ext = "bin"
                        data = img.data
                        if len(data) > max_bytes:
                            diagnostics.add("preview_byte_limit", "Extracted image exceeds the configured byte limit")
                            continue
                        out_name = f"{stem}_{digest[:12]}_p{page_index+1:02d}_img{img_index:02d}.{ext}"
                        out_path = preview_dir / out_name
                        out_path.write_bytes(data)
                        preview_rows.append({
                            "source_pdf": str(p), "source_sha256": digest,
                            "page": page_index + 1, "image_index": img_index,
                            "preview_path": str(out_path), "preview_sha256": hashlib.sha256(data).hexdigest(),
                        })
                        taken += 1
                        report["images_extracted"] = taken
                report["status"] = "EXTRACTED" if taken else "NO_IMAGE_EXTRACTED"
                report["scope"] = "Selected preview images only; no complete image inventory, rendering validation, or visual review."
        except Exception as exc:
            diagnostics.add(type(exc).__name__, str(exc))
        finally:
            report["diagnostic_count"] = diagnostics.count
            report["diagnostics"] = diagnostics.entries
            if diagnostics.count:
                report["status"] = "PARTIAL_OR_FAILED"

    return preview_rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Curate top assets for proof narratives from a local root.")
    ap.add_argument("--icloud-root", default=r"C:\Users\Novac\iCloudDrive")
    ap.add_argument("--scan-root", default="")
    ap.add_argument("--output-root", default=r"C:\LumaTrader\out\ops")
    ap.add_argument("--stale-days", type=int, default=180)
    ap.add_argument("--top-n", type=int, default=200)
    ap.add_argument("--max-doc-bytes", type=int, default=2_500_000)
    ap.add_argument("--max-doc-pages", type=int, default=8)
    ap.add_argument("--max-doc-chars", type=int, default=300_000)
    ap.add_argument("--max-files", type=int, default=0)
    ap.add_argument("--preview-max-docs", type=int, default=30)
    ap.add_argument("--preview-max-images", type=int, default=4)
    ap.add_argument("--progress-every", type=int, default=20000)
    args = ap.parse_args()
    for name in ("max_doc_bytes", "max_doc_pages", "max_doc_chars", "top_n"):
        if getattr(args, name) < 1:
            ap.error(f"--{name.replace('_', '-')} must be positive")
    for name in ("max_files", "preview_max_docs", "preview_max_images"):
        if getattr(args, name) < 0:
            ap.error(f"--{name.replace('_', '-')} must not be negative")

    scan_root_arg = (args.scan_root or args.icloud_root).strip()
    scan_root = Path(scan_root_arg).resolve()
    output_root = Path(args.output_root).resolve()
    tag = now_tag()
    label = "icloud" if "icloud" in str(scan_root).lower() else "local"
    run_dir = output_root / f"{label}_top_assets_{tag}"
    if not scan_root.is_dir():
        raise SystemExit(f"Scan root is not an existing directory: {scan_root}")
    run_dir.mkdir(parents=True, exist_ok=True)

    files_seen = 0
    now = datetime.now(timezone.utc)

    doc_rows: list[dict[str, Any]] = []
    image_rows: list[dict[str, Any]] = []
    interrupted = False

    try:
        for files_seen, p in iter_user_files(scan_root, max_files=args.max_files):
            if int(args.progress_every) > 0 and files_seen % int(args.progress_every) == 0:
                print(
                    f"PROGRESS files_seen={files_seen} docs={len(doc_rows)} "
                    f"images={len(image_rows)} path={p}",
                    flush=True,
                )

            ext = p.suffix.lower()
            if ext not in DOC_EXTS and ext not in IMG_EXTS:
                continue

            try:
                st = p.stat()
            except Exception:
                continue

            size = int(st.st_size)
            modified = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            age_days = max(0.0, (now - modified).total_seconds() / 86400.0)
            stale = age_days > float(args.stale_days)

            if ext in DOC_EXTS:
                parsed = parse_document(
                    p,
                    max_bytes=int(args.max_doc_bytes),
                    max_pages=int(args.max_doc_pages),
                    max_chars=int(args.max_doc_chars),
                )
                text_sample = str(parsed.get("text", ""))
                hits, terms = keyword_hits(p, text_sample)
                score = score_asset(
                    hits=hits,
                    age_days=age_days,
                    has_embedded_images=int(parsed.get("image_objects", 0)) > 0,
                    width=0,
                    height=0,
                    filename=p.name,
                )
                doc_rows.append(
                    {
                        "asset_type": "document",
                        "path": str(p),
                        "ext": ext,
                        "size_bytes": size,
                        "modified_utc": utc_from_ts(st.st_mtime),
                        "age_days": round(age_days, 2),
                        "stale": stale,
                        "broken": not bool(parsed.get("ok", False)),
                        "pages_total": int(parsed.get("pages_total", 0)),
                        "image_objects": int(parsed.get("image_objects", 0)),
                        "pages_with_images": int(parsed.get("pages_with_images", 0)),
                        "inspection_status": parsed.get("inspection_status", "FORMAT_COVERAGE_UNVERIFIED"),
                        "pages_inspected": int(parsed.get("pages_inspected", 0)),
                        "pages_text_extracted": int(parsed.get("pages_text_extracted", 0)),
                        "pages_without_text": int(parsed.get("pages_without_text", 0)),
                        "text_layer_complete": bool(parsed.get("text_layer_complete", False)),
                        "image_inventory_complete": bool(parsed.get("image_inventory_complete", False)),
                        "ocr_performed": False,
                        "source_sha256": parsed.get("source_sha256", ""),
                        "limits_reached": ";".join(parsed.get("limits_reached", [])),
                        "diagnostic_count": int(parsed.get("diagnostic_count", 0)),
                        "diagnostics": json.dumps(parsed.get("diagnostics", []), ensure_ascii=True),
                        "robot_hits": hits.get("robot", 0),
                        "proof_hits": hits.get("proof", 0),
                        "plot_hits": hits.get("plot", 0),
                        "luma_hits": hits.get("luma", 0),
                        "hardware_hits": hits.get("hardware", 0),
                        "matched_terms": ";".join(terms),
                        "score": score,
                        "excerpt": clean_excerpt(text_sample),
                        "error": str(parsed.get("error", "")),
                    }
                )
                continue

            image_info = inspect_image(p)
            hits, terms = keyword_hits(p, "")
            score = score_asset(
                hits=hits,
                age_days=age_days,
                has_embedded_images=False,
                width=int(image_info.get("width", 0)),
                height=int(image_info.get("height", 0)),
                filename=p.name,
            )
            image_rows.append(
                {
                    "asset_type": "image",
                    "path": str(p),
                    "ext": ext,
                    "size_bytes": size,
                    "modified_utc": utc_from_ts(st.st_mtime),
                    "age_days": round(age_days, 2),
                    "stale": stale,
                    "broken": not bool(image_info.get("ok", False)),
                    "width": int(image_info.get("width", 0)),
                    "height": int(image_info.get("height", 0)),
                    "mode": str(image_info.get("mode", "")),
                    "robot_hits": hits.get("robot", 0),
                    "proof_hits": hits.get("proof", 0),
                    "plot_hits": hits.get("plot", 0),
                    "luma_hits": hits.get("luma", 0),
                    "hardware_hits": hits.get("hardware", 0),
                    "matched_terms": ";".join(terms),
                    "score": score,
                    "error": str(image_info.get("error", "")),
                }
            )
    except KeyboardInterrupt:
        interrupted = True
        print("INTERRUPTED writing partial outputs", flush=True)

    eligible_docs = [r for r in doc_rows if not r["stale"] and not r["broken"] and float(r["score"]) > 0]
    eligible_images = [r for r in image_rows if not r["stale"] and not r["broken"] and float(r["score"]) > 0]

    all_eligible: list[dict[str, Any]] = []
    all_eligible.extend(eligible_docs)
    all_eligible.extend(eligible_images)
    all_eligible.sort(key=lambda r: (-float(r.get("score", 0)), float(r.get("age_days", 999999)), str(r.get("path", ""))))

    top_assets = all_eligible[: int(args.top_n)]
    top_robot = [r for r in top_assets if int(r.get("robot_hits", 0)) > 0][:50]
    top_proof_plot = [
        r for r in top_assets
        if int(r.get("proof_hits", 0)) > 0 or int(r.get("plot_hits", 0)) > 0
    ][:80]

    preview_reports: list[dict[str, Any]] = []
    preview_rows = extract_pdf_previews(
        top_docs=top_assets,
        preview_dir=run_dir / "pdf_preview_images",
        max_docs=int(args.preview_max_docs),
        max_images_per_doc=int(args.preview_max_images),
        max_bytes=int(args.max_doc_bytes),
        max_pages=int(args.max_doc_pages),
        reports=preview_reports,
    )

    doc_fields = [
        "asset_type",
        "path",
        "ext",
        "size_bytes",
        "modified_utc",
        "age_days",
        "stale",
        "broken",
        "pages_total",
        "image_objects",
        "pages_with_images",
        "inspection_status", "pages_inspected", "pages_text_extracted", "pages_without_text",
        "text_layer_complete", "image_inventory_complete", "ocr_performed",
        "source_sha256", "limits_reached", "diagnostic_count", "diagnostics",
        "robot_hits",
        "proof_hits",
        "plot_hits",
        "luma_hits",
        "hardware_hits",
        "matched_terms",
        "score",
        "excerpt",
        "error",
    ]

    image_fields = [
        "asset_type",
        "path",
        "ext",
        "size_bytes",
        "modified_utc",
        "age_days",
        "stale",
        "broken",
        "width",
        "height",
        "mode",
        "robot_hits",
        "proof_hits",
        "plot_hits",
        "luma_hits",
        "hardware_hits",
        "matched_terms",
        "score",
        "error",
    ]

    top_fields = [
        "asset_type",
        "path",
        "ext",
        "score",
        "age_days",
        "modified_utc",
        "robot_hits",
        "proof_hits",
        "plot_hits",
        "luma_hits",
        "hardware_hits",
        "matched_terms",
        "stale",
        "broken",
        "inspection_status", "pages_total", "pages_inspected", "text_layer_complete",
        "image_inventory_complete", "ocr_performed", "source_sha256", "limits_reached", "diagnostic_count",
    ]

    write_csv(run_dir / "document_inventory.csv", doc_rows, doc_fields)
    write_csv(run_dir / "image_inventory.csv", image_rows, image_fields)
    write_csv(run_dir / "top_assets.csv", top_assets, top_fields)
    write_csv(run_dir / "top_robot_assets.csv", top_robot, top_fields)
    write_csv(run_dir / "top_proof_plot_assets.csv", top_proof_plot, top_fields)
    write_csv(run_dir / "pdf_preview_images.csv", preview_rows, ["source_pdf", "source_sha256", "page", "image_index", "preview_path", "preview_sha256"])

    summary = {
        "generated_utc": now_iso(),
        "schema": "lumencore.asset_discovery_coverage.v2",
        "claim_boundary": "Keyword-ranked discovery candidates only. Partial PDF scans remain labeled; text-layer extraction is not OCR, visual review, complete notebook access, technical validation, or investment value. Non-PDF format coverage is unverified.",
        "scope": {
            "scan_root": str(scan_root),
            "output_dir": str(run_dir),
            "stale_days": int(args.stale_days),
            "top_n": int(args.top_n),
            "interrupted": interrupted,
            "max_document_bytes": int(args.max_doc_bytes),
            "max_pdf_pages": int(args.max_doc_pages),
            "max_retained_text_characters": int(args.max_doc_chars),
            "configured_file_limit": int(args.max_files),
            "file_limit_reached": bool(args.max_files and files_seen >= args.max_files),
            "full_notebook_access_established": False,
        },
        "counts": {
            "files_seen": files_seen,
            "documents_scanned": len(doc_rows),
            "images_scanned": len(image_rows),
            "documents_broken": sum(1 for r in doc_rows if r["broken"]),
            "pdf_partial_inspections": sum(1 for r in doc_rows if r.get("inspection_status") == "PARTIAL"),
            "pdf_text_layers_inspected": sum(1 for r in doc_rows if r.get("inspection_status") == "TEXT_LAYER_INSPECTED"),
            "pdf_failed_inspections": sum(1 for r in doc_rows if r["ext"] == ".pdf" and r["broken"]),
            "images_broken": sum(1 for r in image_rows if r["broken"]),
            "documents_stale": sum(1 for r in doc_rows if r["stale"]),
            "images_stale": sum(1 for r in image_rows if r["stale"]),
            "eligible_docs": len(eligible_docs),
            "eligible_images": len(eligible_images),
            "top_assets": len(top_assets),
            "top_robot_assets": len(top_robot),
            "top_proof_plot_assets": len(top_proof_plot),
            "pdf_previews_extracted": len(preview_rows),
            "pdf_preview_documents_attempted": len(preview_reports),
            "pdf_preview_holds_or_errors": sum(1 for r in preview_reports if r["status"] not in {"EXTRACTED", "NO_IMAGE_EXTRACTED"}),
        },
        "pdf_preview_reports": preview_reports,
        "top_assets": top_assets[:100],
        "top_robot_assets": top_robot[:50],
        "top_proof_plot_assets": top_proof_plot[:80],
        "evidence_paths": {
            "document_inventory_csv": str(run_dir / "document_inventory.csv"),
            "image_inventory_csv": str(run_dir / "image_inventory.csv"),
            "top_assets_csv": str(run_dir / "top_assets.csv"),
            "top_assets_json": str(run_dir / "top_assets.json"),
            "top_robot_assets_csv": str(run_dir / "top_robot_assets.csv"),
            "top_proof_plot_assets_csv": str(run_dir / "top_proof_plot_assets.csv"),
            "pdf_preview_images_csv": str(run_dir / "pdf_preview_images.csv"),
            "pdf_preview_image_dir": str(run_dir / "pdf_preview_images"),
        },
    }

    (run_dir / "top_assets.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        "# Local Root Top Asset Curation",
        f"Generated UTC: {summary['generated_utc']}",
        "",
        "## Scope",
        f"- Scan root: {scan_root}",
        f"- Stale cutoff: > {int(args.stale_days)} days",
        f"- Top-N selected: {int(args.top_n)}",
        "- Keyword scores rank discovery candidates; they do not score validity or investment readiness.",
        "- PDF inspection covers only the reported text layer and image objects. No OCR or visual review is performed.",
        "- Non-PDF format coverage remains unverified; this inventory is not full notebook access.",
        "",
        "## Counts",
        f"- Files seen: {summary['counts']['files_seen']}",
        f"- Documents scanned: {summary['counts']['documents_scanned']}",
        f"- Images scanned: {summary['counts']['images_scanned']}",
        f"- Documents broken: {summary['counts']['documents_broken']}",
        f"- PDF partial inspections: {summary['counts']['pdf_partial_inspections']}",
        f"- PDF text layers inspected: {summary['counts']['pdf_text_layers_inspected']}",
        f"- Images broken: {summary['counts']['images_broken']}",
        f"- Documents stale: {summary['counts']['documents_stale']}",
        f"- Images stale: {summary['counts']['images_stale']}",
        f"- Eligible top assets: {summary['counts']['top_assets']}",
        f"- Robot-concept assets: {summary['counts']['top_robot_assets']}",
        f"- Proof/plot assets: {summary['counts']['top_proof_plot_assets']}",
        f"- PDF previews extracted: {summary['counts']['pdf_previews_extracted']}",
        "",
        "## Top Assets (first 25)",
        "| Rank | Type | Score | Age Days | Inspection | Path |",
        "|---:|---|---:|---:|---|---|",
    ]

    for idx, row in enumerate(top_assets[:25], start=1):
        md_lines.append(
            f"| {idx} | {row.get('asset_type','')} | {float(row.get('score',0)):.2f} | "
            f"{float(row.get('age_days',0)):.1f} | {row.get('inspection_status','image metadata only')} | {row.get('path','')} |"
        )

    md_lines.extend([
        "",
        "## Evidence Paths",
        f"- {run_dir / 'document_inventory.csv'}",
        f"- {run_dir / 'image_inventory.csv'}",
        f"- {run_dir / 'top_assets.csv'}",
        f"- {run_dir / 'top_assets.json'}",
        f"- {run_dir / 'top_robot_assets.csv'}",
        f"- {run_dir / 'top_proof_plot_assets.csv'}",
        f"- {run_dir / 'pdf_preview_images.csv'}",
        f"- {run_dir / 'pdf_preview_images'}",
    ])

    (run_dir / "top_assets.md").write_text("\n".join(md_lines), encoding="utf-8")

    latest_txt = output_root / f"{label}_top_assets_latest.txt"
    latest_json = output_root / f"{label}_top_assets_latest.json"
    latest_txt.write_text(run_dir.name, encoding="ascii")
    latest_json.write_text(
        json.dumps(
            {
                "generated_utc": summary["generated_utc"],
                "latest_run": run_dir.name,
                "run_dir": str(run_dir),
                "summary_json": str(run_dir / "top_assets.json"),
                "summary_md": str(run_dir / "top_assets.md"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"RUN_DIR={run_dir}")
    print(f"DOCS_SCANNED={len(doc_rows)}")
    print(f"IMAGES_SCANNED={len(image_rows)}")
    print(f"TOP_ASSETS={len(top_assets)}")
    print(f"TOP_ROBOT={len(top_robot)}")
    print(f"TOP_PROOF_PLOT={len(top_proof_plot)}")
    print(f"PDF_PREVIEWS={len(preview_rows)}")
    print(f"LATEST_TXT={latest_txt}")
    print(f"LATEST_JSON={latest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
