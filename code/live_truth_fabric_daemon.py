from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC = OUT / "execution"
TRUTH_DIR = OUT / "live_truth_fabric"

CROSS_OPT_FILE = OUT / "cross_sector_optimization_report.json"
CROSS_PRED_FILE = OUT / "cross_sector_failure_predictions.jsonl"
SCOUT_PRIMARY = ROOT / "LamaScout" / "reports" / "artist_scout_summary.json"
SCOUT_FALLBACK = OUT / "lumascout" / "reports" / "artist_scout_summary.json"

ROUTER_FILE = TRUTH_DIR / "live_truth_router.json"
ROUTER_JSONL = TRUTH_DIR / "live_truth_router.jsonl"
MANIFEST_FILE = TRUTH_DIR / "live_truth_manifest.json"
HEARTBEAT_FILE = EXEC / "live_truth_fabric_heartbeat.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def tail_jsonl(path: Path, limit: int = 80) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]
    except Exception:
        return []


def atomic_write_json(path: Path, payload: Any, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=indent), encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def load_scout_summary() -> dict[str, Any]:
    data = load_json(SCOUT_PRIMARY, None)
    if isinstance(data, dict):
        return data
    data = load_json(SCOUT_FALLBACK, None)
    return data if isinstance(data, dict) else {}


def geometric_router(cross_opt: dict[str, Any], cross_preds: list[dict[str, Any]], scout: dict[str, Any]) -> dict[str, Any]:
    aggregate = cross_opt.get("aggregate", {}) if isinstance(cross_opt, dict) else {}
    prevented_pct = _safe_float(aggregate.get("prevented_pct"), 0.0)
    projected = _safe_float(aggregate.get("projected_failure_cost_usd"), 0.0)
    avoided = _safe_float(aggregate.get("estimated_avoided_cost_usd"), 0.0)

    pred_conf = 0.0
    if cross_preds:
        pred_conf = sum(_safe_float(r.get("confidence"), 0.0) for r in cross_preds) / max(len(cross_preds), 1)

    scout_ranked = scout.get("top_ranked", scout.get("artists", [])) if isinstance(scout, dict) else []
    scout_ranked = scout_ranked if isinstance(scout_ranked, list) else []
    scout_signal_density = min(len(scout_ranked) / 50.0, 1.0)

    # Bubble-lattice style non-linear fusion score.
    curvature = (prevented_pct / 100.0) ** 0.5 if prevented_pct > 0 else 0.0
    resonance = min(max(pred_conf, 0.0), 1.0)
    persistence = min((avoided / max(projected, 1.0)), 1.0) if projected > 0 else 0.0
    scout_phase = scout_signal_density

    lattice_score = (
        0.34 * curvature
        + 0.27 * resonance
        + 0.24 * persistence
        + 0.15 * scout_phase
    )

    mode = "adaptive_hold"
    if lattice_score >= 0.72:
        mode = "aggressive_expansion"
    elif lattice_score >= 0.56:
        mode = "targeted_expansion"
    elif lattice_score >= 0.42:
        mode = "selective_execution"

    return {
        "generated_utc": now_utc(),
        "router_version": "live_truth_fabric_v1",
        "mode": mode,
        "lattice_score": round(lattice_score, 6),
        "geometry": {
            "curvature": round(curvature, 6),
            "resonance": round(resonance, 6),
            "persistence": round(persistence, 6),
            "scout_phase": round(scout_phase, 6),
        },
        "cross_sector": {
            "prevented_pct": round(prevented_pct, 6),
            "projected_failure_cost_usd": round(projected, 2),
            "estimated_avoided_cost_usd": round(avoided, 2),
            "prediction_count": len(cross_preds),
            "avg_prediction_confidence": round(pred_conf, 6),
        },
        "digital_scout": {
            "candidate_count": len(scout_ranked),
            "signal_density": round(scout_signal_density, 6),
            "top_candidate": (scout_ranked[0] if scout_ranked else {}),
        },
        "routing_actions": {
            "node_red": {
                "channel": "luma/live_truth",
                "hint": "Poll /api/live-truth/fabric and route cues by mode + lattice_score",
            },
            "unity": {
                "channel": "live_truth_overlay",
                "hint": "Drive scene intensity from geometry.curvature and resonance",
            },
            "vps": {
                "hint": "Replicate out/live_truth_fabric to VPS for edge-serving + observability",
            },
            "lumen_core_ai": {
                "hint": "Consume /api/live-truth/fabric as auditable runtime truth input",
            },
        },
    }


def build_manifest(router: dict[str, Any]) -> dict[str, Any]:
    source_files = [
        CROSS_OPT_FILE,
        CROSS_PRED_FILE,
        SCOUT_PRIMARY,
        SCOUT_FALLBACK,
        ROUTER_FILE,
    ]
    artifacts = []
    for p in source_files:
        if not p.exists():
            continue
        artifacts.append(
            {
                "path": str(p),
                "sha256": sha256_file(p),
                "size_bytes": int(p.stat().st_size),
                "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
        )
    payload_hash = hashlib.sha256(json.dumps(router, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "generated_utc": now_utc(),
        "manifest_version": "live_truth_manifest_v1",
        "payload_sha256": payload_hash,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def run_once() -> dict[str, Any]:
    cross_opt = load_json(CROSS_OPT_FILE, {})
    cross_preds = tail_jsonl(CROSS_PRED_FILE, limit=80)
    scout = load_scout_summary()

    router = geometric_router(cross_opt, cross_preds, scout)
    atomic_write_json(ROUTER_FILE, router)
    append_jsonl(ROUTER_JSONL, router)

    manifest = build_manifest(router)
    atomic_write_json(MANIFEST_FILE, manifest)

    heartbeat = {
        "generated_utc": now_utc(),
        "service": "live_truth_fabric",
        "status": "ok",
        "mode": router.get("mode", "unknown"),
        "lattice_score": router.get("lattice_score", 0.0),
        "payload_sha256": manifest.get("payload_sha256", ""),
        "artifact_count": manifest.get("artifact_count", 0),
    }
    atomic_write_json(HEARTBEAT_FILE, heartbeat)
    return heartbeat


def main() -> None:
    parser = argparse.ArgumentParser(description="Live truth fabric daemon: cross-sector + digital scout fusion")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=30, help="Loop interval seconds")
    args = parser.parse_args()

    hb = run_once()
    print(f"[live_truth_fabric] mode={hb.get('mode')} score={hb.get('lattice_score')} sha={str(hb.get('payload_sha256',''))[:12]}", flush=True)
    if not args.loop:
        return

    interval = max(5, int(args.interval))
    while True:
        time.sleep(interval)
        hb = run_once()
        print(f"[live_truth_fabric] mode={hb.get('mode')} score={hb.get('lattice_score')} sha={str(hb.get('payload_sha256',''))[:12]}", flush=True)


if __name__ == "__main__":
    main()
