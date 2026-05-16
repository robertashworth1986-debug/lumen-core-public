from __future__ import annotations

import argparse
import csv
import html
import json
import logging
import os
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

logging.getLogger("pypdf").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", module="pypdf")

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


def parse_pdf(path: Path, max_pages: int, max_chars: int) -> dict[str, Any]:
    if PdfReader is None:
        return {
            "ok": False,
            "error": "pypdf_not_installed",
            "text": "",
            "pages_total": 0,
            "image_objects": 0,
            "pages_with_images": 0,
        }

    try:
        with path.open("rb") as fh:
            head = fh.read(8)
        if not head.startswith(b"%PDF-"):
            return {
                "ok": False,
                "error": "invalid_pdf_header",
                "text": "",
                "pages_total": 0,
                "image_objects": 0,
                "pages_with_images": 0,
            }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "text": "",
            "pages_total": 0,
            "image_objects": 0,
            "pages_with_images": 0,
        }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reader = PdfReader(str(path), strict=False)
    text_parts: list[str] = []
    pages_total = len(reader.pages)
    img_total = 0
    img_pages = 0
    remaining = max_chars

    for i, page in enumerate(reader.pages):
        page_img_count = 0
        try:
            page_img_count = len(getattr(page, "images", []))
        except Exception:
            page_img_count = 0

        if page_img_count > 0:
            img_pages += 1
        img_total += page_img_count

        if i < max_pages and remaining > 0:
            txt = ""
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            if txt:
                txt = txt[:remaining]
                text_parts.append(txt)
                remaining -= len(txt)

    return {
        "ok": True,
        "error": "",
        "text": "\n".join(text_parts),
        "pages_total": pages_total,
        "image_objects": img_total,
        "pages_with_images": img_pages,
    }


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
            return parse_pdf(path, max_pages=max_pages, max_chars=max_chars)
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
) -> list[dict[str, Any]]:
    preview_rows: list[dict[str, Any]] = []
    if PdfReader is None:
        return preview_rows

    preview_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    for doc in top_docs:
        if processed >= max_docs:
            break
        p = Path(str(doc.get("path", "")))
        if p.suffix.lower() != ".pdf":
            continue
        if not p.exists():
            continue
        try:
            with p.open("rb") as fh:
                head = fh.read(8)
            if not head.startswith(b"%PDF-"):
                continue

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                reader = PdfReader(str(p), strict=False)
            taken = 0
            stem = safe_name(p.stem)
            for page_idx, page in enumerate(reader.pages, start=1):
                if taken >= max_images_per_doc:
                    break
                for img_idx, img in enumerate(getattr(page, "images", []), start=1):
                    if taken >= max_images_per_doc:
                        break
                    ext = "bin"
                    if "." in img.name:
                        ext = img.name.rsplit(".", 1)[-1].lower()
                    if ext not in {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff", "jp2", "jpx"}:
                        ext = "bin"

                    out_name = f"{stem}_p{page_idx:02d}_img{img_idx:02d}.{ext}"
                    out_path = preview_dir / out_name
                    out_path.write_bytes(img.data)
                    preview_rows.append(
                        {
                            "source_pdf": str(p),
                            "page": page_idx,
                            "image_index": img_idx,
                            "preview_path": str(out_path),
                        }
                    )
                    taken += 1
            processed += 1
        except Exception:
            continue

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

    scan_root_arg = (args.scan_root or args.icloud_root).strip()
    scan_root = Path(scan_root_arg).resolve()
    output_root = Path(args.output_root).resolve()
    tag = now_tag()
    label = "icloud" if "icloud" in str(scan_root).lower() else "local"
    run_dir = output_root / f"{label}_top_assets_{tag}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if not scan_root.exists():
        raise SystemExit(f"Scan root missing: {scan_root}")

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

    preview_rows = extract_pdf_previews(
        top_docs=top_assets,
        preview_dir=run_dir / "pdf_preview_images",
        max_docs=int(args.preview_max_docs),
        max_images_per_doc=int(args.preview_max_images),
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
    ]

    write_csv(run_dir / "document_inventory.csv", doc_rows, doc_fields)
    write_csv(run_dir / "image_inventory.csv", image_rows, image_fields)
    write_csv(run_dir / "top_assets.csv", top_assets, top_fields)
    write_csv(run_dir / "top_robot_assets.csv", top_robot, top_fields)
    write_csv(run_dir / "top_proof_plot_assets.csv", top_proof_plot, top_fields)
    write_csv(run_dir / "pdf_preview_images.csv", preview_rows, ["source_pdf", "page", "image_index", "preview_path"])

    summary = {
        "generated_utc": now_iso(),
        "scope": {
            "scan_root": str(scan_root),
            "output_dir": str(run_dir),
            "stale_days": int(args.stale_days),
            "top_n": int(args.top_n),
            "interrupted": interrupted,
        },
        "counts": {
            "files_seen": files_seen,
            "documents_scanned": len(doc_rows),
            "images_scanned": len(image_rows),
            "documents_broken": sum(1 for r in doc_rows if r["broken"]),
            "images_broken": sum(1 for r in image_rows if r["broken"]),
            "documents_stale": sum(1 for r in doc_rows if r["stale"]),
            "images_stale": sum(1 for r in image_rows if r["stale"]),
            "eligible_docs": len(eligible_docs),
            "eligible_images": len(eligible_images),
            "top_assets": len(top_assets),
            "top_robot_assets": len(top_robot),
            "top_proof_plot_assets": len(top_proof_plot),
            "pdf_previews_extracted": len(preview_rows),
        },
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
        "",
        "## Counts",
        f"- Files seen: {summary['counts']['files_seen']}",
        f"- Documents scanned: {summary['counts']['documents_scanned']}",
        f"- Images scanned: {summary['counts']['images_scanned']}",
        f"- Documents broken: {summary['counts']['documents_broken']}",
        f"- Images broken: {summary['counts']['images_broken']}",
        f"- Documents stale: {summary['counts']['documents_stale']}",
        f"- Images stale: {summary['counts']['images_stale']}",
        f"- Eligible top assets: {summary['counts']['top_assets']}",
        f"- Robot-concept assets: {summary['counts']['top_robot_assets']}",
        f"- Proof/plot assets: {summary['counts']['top_proof_plot_assets']}",
        f"- PDF previews extracted: {summary['counts']['pdf_previews_extracted']}",
        "",
        "## Top Assets (first 25)",
        "| Rank | Type | Score | Age Days | Path |",
        "|---:|---|---:|---:|---|",
    ]

    for idx, row in enumerate(top_assets[:25], start=1):
        md_lines.append(
            f"| {idx} | {row.get('asset_type','')} | {float(row.get('score',0)):.2f} | "
            f"{float(row.get('age_days',0)):.1f} | {row.get('path','')} |"
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
