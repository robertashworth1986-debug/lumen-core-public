from __future__ import annotations
import shutil, hashlib, re
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

CANON = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
INDEX = CANON / "data" / "root_registry" / "MASTER_ROOT_REGISTRY.csv"
PROMO = CANON / "data" / "promoted_raw"
CLEAN = CANON / "clean_data"

PROMO.mkdir(parents=True, exist_ok=True)
CLEAN.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTS = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".txt"}
PROMOTE_ROLES = {"FEEDER_DATA", "ACTIVE_LAB"}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def safe(x: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", x).strip("_")[:180]

def sig(x: str) -> str:
    return hashlib.sha1(x.encode("utf-8", errors="ignore")).hexdigest()[:10]

def is_dataset_file(p: Path) -> bool:
    name = p.name.lower()
    ext = p.suffix.lower()
    if ext not in ALLOWED_EXTS:
        return False
    bad = ["chain_of_custody", "sha256", "site_contact", "proof", "ledger", "manifest", "inventory", "report", "summary"]
    if any(b in name for b in bad):
        return False
    return True

roots = pd.read_csv(INDEX)
rows = []
promoted = []

for _, r in roots.iterrows():
    root = Path(str(r["root"]))
    role = str(r["role"])
    if role not in PROMOTE_ROLES or not root.exists():
        continue

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part.lower() in {".venv","venv","env311","__pycache__","site-packages","temp","appdata","scripts","lib"} for part in p.parts):
            continue
        if not is_dataset_file(p):
            continue

        ext = p.suffix.lower()
        rel = safe(str(p.relative_to(root)))
        base = f"{safe(root.name)}__{rel}__{sig(str(p))}"
        dest = PROMO / f"{base}{ext}"

        try:
            if not dest.exists():
                shutil.copy2(p, dest)

            clean_dest = ""
            if ext in {".csv", ".tsv"}:
                clean_file = CLEAN / f"{base}.csv"
                if not clean_file.exists():
                    shutil.copy2(p, clean_file)
                clean_dest = str(clean_file)

            promoted.append({
                "source_root": str(root),
                "role": role,
                "source_file": str(p),
                "promoted_file": str(dest),
                "clean_data_file": clean_dest,
                "ext": ext,
                "promoted_utc": utc_now()
            })
        except Exception as e:
            rows.append({
                "source_root": str(root),
                "role": role,
                "source_file": str(p),
                "status": f"failed: {e}"
            })

if promoted:
    pdf = pd.DataFrame(promoted)
else:
    pdf = pd.DataFrame(columns=["source_root","role","source_file","promoted_file","clean_data_file","ext","promoted_utc"])

if rows:
    ldf = pd.DataFrame(rows)
else:
    ldf = pd.DataFrame(columns=["source_root","role","source_file","status"])

pdf.to_csv(CANON / "data" / "root_registry" / "PROMOTED_DATASET_INDEX.csv", index=False)
ldf.to_csv(CANON / "data" / "root_registry" / "PROMOTION_LOG.csv", index=False)

print(CANON / "data" / "root_registry" / "PROMOTED_DATASET_INDEX.csv")
print(CANON / "data" / "root_registry" / "PROMOTION_LOG.csv")
print(PROMO)
print(CLEAN)
