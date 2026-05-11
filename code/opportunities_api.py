"""FastAPI router for opportunity harvest + filler bot.

Endpoints:
  GET  /api/opportunities/ranked         -> latest ranked.json
  GET  /api/opportunities/queue          -> queue.jsonl as array
  POST /api/opportunities/harvest        -> trigger harvester (synchronous)
  POST /api/opportunities/fill           -> trigger filler bot (synchronous)
  GET  /api/opportunities/package/{slug} -> read a drafted package
  POST /api/opportunities/{slug}/approve -> mark draft as approved-for-submit
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "opportunities"
PY = sys.executable
OUT.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


def _read_json(p: Path) -> Any:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


@router.get("/ranked")
def get_ranked(limit: int = 50) -> dict:
    payload = _read_json(OUT / "ranked.json")
    if not payload:
        return {"error": "no harvest yet -- POST /api/opportunities/harvest"}
    recs = payload.get("records", [])[:limit]
    return {
        "generated_utc": payload.get("generated_utc"),
        "total_actionable": payload.get("total_actionable"),
        "records": recs,
    }


@router.get("/queue")
def get_queue() -> dict:
    p = OUT / "queue.jsonl"
    if not p.exists():
        return {"queue": []}
    items = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"count": len(items), "queue": items}


class HarvestArgs(BaseModel):
    min_score: float = 0.30


class FillArgs(BaseModel):
    min_score: float = 0.40
    limit: int = 25


def _run(script: str, args: list[str]) -> dict:
    try:
        proc = subprocess.run(
            [PY, str(ROOT / "code" / script), *args],
            capture_output=True, text=True, timeout=600,
        )
        return {
            "rc": proc.returncode,
            "stdout_tail": (proc.stdout or "").splitlines()[-15:],
            "stderr_tail": (proc.stderr or "").splitlines()[-5:],
        }
    except subprocess.TimeoutExpired:
        return {"rc": -1, "error": "timeout"}


@router.post("/harvest")
def trigger_harvest(args: HarvestArgs) -> dict:
    return _run("opportunity_harvester.py", ["--min-score", str(args.min_score)])


@router.post("/fill")
def trigger_fill(args: FillArgs) -> dict:
    return _run("opportunity_filler.py",
                ["--min-score", str(args.min_score), "--limit", str(args.limit)])


@router.get("/package/{slug}")
def get_package(slug: str) -> dict:
    p = OUT / slug
    if not p.is_dir() or ".." in slug or "/" in slug or "\\" in slug:
        raise HTTPException(404, f"package {slug} not found")
    files = {}
    for name in ("application.json", "approval_state.json", "cover_letter.md",
                 "technical_brief.md", "SUBMIT_HOWTO.md"):
        f = p / name
        if f.exists():
            files[name] = f.read_text(encoding="utf-8")
    return {"slug": slug, "files": files}


class ApprovalPatch(BaseModel):
    state: str  # "approved" | "submitted" | "withdrawn"
    notes: str = ""


@router.post("/{slug}/approve")
def approve(slug: str, patch: ApprovalPatch) -> dict:
    if patch.state not in {"approved", "submitted", "withdrawn"}:
        raise HTTPException(400, "state must be approved|submitted|withdrawn")
    p = OUT / slug / "approval_state.json"
    if not p.exists():
        raise HTTPException(404, f"package {slug} not found")
    cur = json.loads(p.read_text(encoding="utf-8"))
    cur["state"] = patch.state
    cur["notes"] = patch.notes
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    tmp.replace(p)
    return {"slug": slug, "state": patch.state, "ok": True}
