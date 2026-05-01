import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
PACK_DIR = OUT / "evidence_pack"
PACK_DIR.mkdir(parents=True, exist_ok=True)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def list_artifacts() -> List[Path]:
    patterns = [
        EXEC_OUT / "institutional_live_selection.json",
        EXEC_OUT / "institutional_summary.json",
        EXEC_OUT / "institutional_top10.csv",
        EXEC_OUT / "institutional_leaderboard.csv",
        EXEC_OUT / "institutional_champion_families.csv",
        EXEC_OUT / "institutional_champion_lineages.json",
        EXEC_OUT / "trade_log.json",
        EXEC_OUT / "portfolio_summary.json",
        EXEC_OUT / "execution_audit_chain.jsonl",
        OUT / "institutional_daily_report.json",
        OUT / "institutional_daily_report.csv",
        OUT / "institutional_daily_report_sha256.json",
        ROOT / "config" / "runtime_control.json",
        ROOT / "config" / "paper_trader_runtime.json",
        ROOT / "config" / "live_source_registry.json",
    ]
    return [p for p in patterns if p.exists()]


def summarize_trade_log(path: Path) -> Dict:
    if not path.exists():
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "realized_pnl": 0.0,
        }
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        closed = [r for r in rows if str(r.get("status", "")).upper() == "CLOSED"]
        wins = [r for r in closed if float(r.get("pnl", 0.0) or 0.0) > 0]
        losses = [r for r in closed if float(r.get("pnl", 0.0) or 0.0) < 0]
        pnl = sum(float(r.get("pnl", 0.0) or 0.0) for r in closed)
        return {
            "trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": (len(wins) / len(closed)) if len(closed) else 0.0,
            "realized_pnl": pnl,
        }
    except Exception:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "realized_pnl": 0.0,
        }


def build_pack():
    artifacts = list_artifacts()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    manifest = {
        "generated_utc": now_utc(),
        "pack_version": "1.0",
        "artifact_count": len(artifacts),
        "artifacts": [],
        "performance_summary": summarize_trade_log(EXEC_OUT / "trade_log.json"),
    }

    csv_path = PACK_DIR / f"artifact_hash_ledger_{stamp}.csv"
    json_path = PACK_DIR / f"artifact_hash_manifest_{stamp}.json"
    zip_path = PACK_DIR / f"institutional_evidence_pack_{stamp}.zip"

    with csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["path", "bytes", "sha256", "modified_utc"])
        for p in artifacts:
            digest = sha256_file(p)
            stat = p.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            rel = str(p.relative_to(ROOT))
            writer.writerow([rel, stat.st_size, digest, modified])
            manifest["artifacts"].append({
                "path": rel,
                "bytes": stat.st_size,
                "sha256": digest,
                "modified_utc": modified,
            })

    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest["manifest_sha256"] = manifest_hash
    json_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, arcname=csv_path.name)
        zf.write(json_path, arcname=json_path.name)
        for p in artifacts:
            zf.write(p, arcname=str(p.relative_to(ROOT)))

    print("EVIDENCE PACK BUILT")
    print(csv_path)
    print(json_path)
    print(zip_path)


if __name__ == "__main__":
    build_pack()
