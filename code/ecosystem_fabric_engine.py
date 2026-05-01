from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from execution.audit_chain import AuditChain

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "ecosystem_engine_config.json"
MASTER_REGISTRY_PATH = ROOT / "data" / "root_registry" / "MASTER_ROOT_REGISTRY.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def parse_utc(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        cleaned = str(text).replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except Exception:
        return None


def safe_rel(path: Path, base: Path = ROOT) -> str:
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


@dataclass
class CrawlSettings:
    max_files_per_root: int
    max_relevant_hits_per_root: int
    skip_dir_names: set[str]
    include_extensions: set[str]
    relevance_keywords: list[str]


class EcosystemFabricEngine:
    def __init__(self, include_root_paths: list[str] | None = None, use_master_registry: bool = True):
        self.config = read_json(CONFIG_PATH, {})
        crawl_cfg = self.config.get("crawl", {}) if isinstance(self.config, dict) else {}
        self.settings = CrawlSettings(
            max_files_per_root=int(crawl_cfg.get("max_files_per_root", 25000)),
            max_relevant_hits_per_root=int(crawl_cfg.get("max_relevant_hits_per_root", 250)),
            skip_dir_names={str(x).lower() for x in crawl_cfg.get("skip_dir_names", [])},
            include_extensions={str(x).lower() for x in crawl_cfg.get("include_extensions", [])},
            relevance_keywords=[str(x).lower() for x in crawl_cfg.get("relevance_keywords", [])],
        )
        self.include_root_paths = include_root_paths or []
        self.use_master_registry = use_master_registry

        audit_cfg = self.config.get("audit", {}) if isinstance(self.config, dict) else {}
        self.chain_file = ROOT / str(audit_cfg.get("chain_file", "out/ecosystem/ecosystem_audit_chain.jsonl"))
        self.frozen_delta_file = ROOT / str(audit_cfg.get("frozen_delta_file", "out/ecosystem/ecosystem_frozen_deltas.jsonl"))
        self.snapshot_file = ROOT / str(audit_cfg.get("snapshot_file", "out/ecosystem/ecosystem_master_snapshot.json"))
        self.root_inventory_file = ROOT / str(audit_cfg.get("root_inventory_file", "out/ecosystem/ecosystem_root_inventory.json"))
        self.relevant_inventory_file = ROOT / str(audit_cfg.get("relevant_inventory_file", "out/ecosystem/ecosystem_relevant_inventory.json"))
        self.layer_status_file = ROOT / str(audit_cfg.get("layer_status_file", "out/ecosystem/ecosystem_layer_status.json"))
        self.source_health_file = ROOT / str(audit_cfg.get("source_health_file", "out/ecosystem/ecosystem_live_source_health.json"))

        self.audit = AuditChain(self.chain_file)

    def _iter_files(self, root: Path) -> Iterable[Path]:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() not in self.settings.skip_dir_names]
            for name in filenames:
                yield Path(dirpath) / name

    def _is_relevant(self, file_path: Path) -> bool:
        s = str(file_path).lower()
        return any(k in s for k in self.settings.relevance_keywords)

    def _file_signature(self, file_path: Path) -> str:
        st = file_path.stat()
        raw = f"{safe_rel(file_path)}|{st.st_size}|{int(st.st_mtime)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _crawl_one_root(self, root_path: Path, role: str = "UNCLASSIFIED") -> tuple[dict[str, Any], list[dict[str, Any]]]:
        scanned = 0
        ext_counter: Counter[str] = Counter()
        relevant_hits: list[dict[str, Any]] = []
        signatures: list[str] = []
        truncated = False

        if not root_path.exists():
            return (
                {
                    "root": str(root_path),
                    "role": role,
                    "exists": False,
                    "scanned_files": 0,
                    "truncated": False,
                    "extension_distribution": {},
                    "root_digest": "missing",
                    "relevant_hits": 0,
                },
                [],
            )

        for fp in self._iter_files(root_path):
            if scanned >= self.settings.max_files_per_root:
                truncated = True
                break
            try:
                ext = fp.suffix.lower()
                if self.settings.include_extensions and ext not in self.settings.include_extensions:
                    continue
                scanned += 1
                ext_counter[ext or "<none>"] += 1

                if self._is_relevant(fp) and len(relevant_hits) < self.settings.max_relevant_hits_per_root:
                    st = fp.stat()
                    relevant_hits.append(
                        {
                            "root": str(root_path),
                            "role": role,
                            "path": str(fp),
                            "relative_path": safe_rel(fp, root_path),
                            "size": st.st_size,
                            "modified_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                        }
                    )
                signatures.append(self._file_signature(fp))
            except Exception:
                continue

        digest_seed = "|".join(sorted(signatures)[:5000])
        root_digest = hashlib.sha256(digest_seed.encode("utf-8")).hexdigest() if digest_seed else "empty"

        summary = {
            "root": str(root_path),
            "role": role,
            "exists": True,
            "scanned_files": scanned,
            "truncated": truncated,
            "extension_distribution": dict(ext_counter.most_common(20)),
            "root_digest": root_digest,
            "relevant_hits": len(relevant_hits),
        }
        return summary, relevant_hits

    def _collect_roots(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        if self.use_master_registry:
            master = read_json(MASTER_REGISTRY_PATH, [])
            if isinstance(master, list):
                for item in master:
                    if not isinstance(item, dict):
                        continue
                    root = str(item.get("root", "")).strip()
                    if not root:
                        continue
                    rows.append({"root": root, "role": str(item.get("role", "UNCLASSIFIED"))})

        for root in self.include_root_paths:
            cleaned = str(root).strip()
            if cleaned:
                rows.append({"root": cleaned, "role": "EXPLICIT_INCLUDE"})

        seen = set()
        deduped: list[dict[str, str]] = []
        for r in rows:
            key = r["root"].lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(r)
        return deduped

    def _layer_status(self) -> dict[str, Any]:
        layers = self.config.get("layer_registry", []) if isinstance(self.config, dict) else []
        out_layers: list[dict[str, Any]] = []

        for layer in layers:
            if not isinstance(layer, dict):
                continue
            name = str(layer.get("name", "unknown"))
            entrypoint = ROOT / str(layer.get("entrypoint", ""))
            runner = ROOT / str(layer.get("runner", "")) if layer.get("runner") else None
            outputs = [ROOT / str(o) for o in (layer.get("outputs", []) or [])]

            output_status = []
            for o in outputs:
                exists = o.exists()
                output_status.append(
                    {
                        "path": safe_rel(o),
                        "exists": exists,
                        "bytes": o.stat().st_size if exists else 0,
                    }
                )

            standalone_ready = entrypoint.exists() and (runner.exists() if runner else True)
            output_ready = bool(output_status) and all(x.get("exists") for x in output_status)

            out_layers.append(
                {
                    "name": name,
                    "entrypoint": safe_rel(entrypoint),
                    "runner": safe_rel(runner) if runner else "n/a",
                    "standalone_ready": standalone_ready,
                    "output_ready": output_ready,
                    "outputs": output_status,
                }
            )

        return {
            "generated_utc": now_utc(),
            "layers": out_layers,
            "standalone_ready_count": sum(1 for x in out_layers if x.get("standalone_ready")),
            "output_ready_count": sum(1 for x in out_layers if x.get("output_ready")),
            "total_layers": len(out_layers),
        }

    def _source_health(self) -> dict[str, Any]:
        src_cfg = self.config.get("sources", {}) if isinstance(self.config, dict) else {}
        registry = ROOT / str(src_cfg.get("registry_path", "config/live_source_registry.json"))
        freshness_hours = float(src_cfg.get("freshness_hours", 24))
        data = read_json(registry, {})

        rows = []
        for s in data.get("sources", []) if isinstance(data, dict) else []:
            if not isinstance(s, dict):
                continue
            env_name = str(s.get("env", "")).strip()
            env_present = bool(os.getenv(env_name, "").strip()) if env_name else False
            probe_time = parse_utc(str(s.get("last_probe_utc", "")))
            fresh = False
            if probe_time is not None:
                age_hours = (datetime.now(timezone.utc) - probe_time).total_seconds() / 3600.0
                fresh = age_hours <= freshness_hours
            rows.append(
                {
                    "source": s.get("source", "n/a"),
                    "sector": s.get("sector", "n/a"),
                    "status": s.get("status", "n/a"),
                    "env": env_name,
                    "env_present_now": env_present,
                    "last_probe_utc": s.get("last_probe_utc", "n/a"),
                    "probe_fresh": fresh,
                }
            )

        return {
            "generated_utc": now_utc(),
            "registry": safe_rel(registry),
            "total_sources": len(rows),
            "env_present_count": sum(1 for r in rows if r.get("env_present_now")),
            "fresh_probe_count": sum(1 for r in rows if r.get("probe_fresh")),
            "sources": rows,
        }

    def _frozen_delta(self, root_inventory: dict[str, Any], layer_status: dict[str, Any], source_health: dict[str, Any]) -> dict[str, Any]:
        prev = read_json(self.snapshot_file, {})

        prev_roots = {
            str(r.get("root", "")): str(r.get("root_digest", ""))
            for r in prev.get("root_inventory", {}).get("roots", [])
            if isinstance(r, dict)
        }
        curr_roots = {
            str(r.get("root", "")): str(r.get("root_digest", ""))
            for r in root_inventory.get("roots", [])
            if isinstance(r, dict)
        }

        changed_roots = []
        for root, digest in curr_roots.items():
            if prev_roots.get(root) != digest:
                changed_roots.append(root)

        prev_layer_ready = int(prev.get("layer_status", {}).get("output_ready_count", 0))
        curr_layer_ready = int(layer_status.get("output_ready_count", 0))

        prev_fresh = int(prev.get("source_health", {}).get("fresh_probe_count", 0))
        curr_fresh = int(source_health.get("fresh_probe_count", 0))

        row = {
            "generated_utc": now_utc(),
            "changed_root_count": len(changed_roots),
            "changed_roots": changed_roots,
            "layer_output_ready_delta": curr_layer_ready - prev_layer_ready,
            "source_fresh_delta": curr_fresh - prev_fresh,
        }
        append_jsonl(self.frozen_delta_file, row)
        return row

    def run_once(self) -> dict[str, Any]:
        roots = self._collect_roots()
        root_summaries: list[dict[str, Any]] = []
        relevant_hits: list[dict[str, Any]] = []

        for root in roots:
            summary, hits = self._crawl_one_root(Path(root["root"]), role=root.get("role", "UNCLASSIFIED"))
            root_summaries.append(summary)
            relevant_hits.extend(hits)

        root_inventory = {
            "generated_utc": now_utc(),
            "total_roots": len(root_summaries),
            "roots": root_summaries,
        }
        relevant_inventory = {
            "generated_utc": now_utc(),
            "total_hits": len(relevant_hits),
            "hits": relevant_hits,
        }

        layer_status = self._layer_status()
        source_health = self._source_health()

        delta = self._frozen_delta(root_inventory, layer_status, source_health)

        snapshot = {
            "generated_utc": now_utc(),
            "profile": self.config.get("profile", "n/a") if isinstance(self.config, dict) else "n/a",
            "root_inventory": root_inventory,
            "layer_status": layer_status,
            "source_health": source_health,
            "frozen_delta": delta,
            "artifacts": {
                "root_inventory_file": safe_rel(self.root_inventory_file),
                "relevant_inventory_file": safe_rel(self.relevant_inventory_file),
                "layer_status_file": safe_rel(self.layer_status_file),
                "source_health_file": safe_rel(self.source_health_file),
                "frozen_delta_file": safe_rel(self.frozen_delta_file),
                "audit_chain_file": safe_rel(self.chain_file),
            },
        }

        write_json(self.root_inventory_file, root_inventory)
        write_json(self.relevant_inventory_file, relevant_inventory)
        write_json(self.layer_status_file, layer_status)
        write_json(self.source_health_file, source_health)
        write_json(self.snapshot_file, snapshot)

        chain_event = {
            "profile": snapshot.get("profile"),
            "total_roots": root_inventory.get("total_roots", 0),
            "total_relevant_hits": relevant_inventory.get("total_hits", 0),
            "standalone_ready_count": layer_status.get("standalone_ready_count", 0),
            "output_ready_count": layer_status.get("output_ready_count", 0),
            "total_sources": source_health.get("total_sources", 0),
            "fresh_probe_count": source_health.get("fresh_probe_count", 0),
            "changed_root_count": delta.get("changed_root_count", 0),
            "snapshot_file": safe_rel(self.snapshot_file),
        }
        self.audit.append(event_type="ecosystem_master_snapshot", payload=chain_event)

        return snapshot


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Luma ecosystem fabric engine: roots + layers + live source health + proof chain")
    p.add_argument("--daemon", action="store_true", help="Run continuously")
    p.add_argument("--interval-sec", type=int, default=300, help="Daemon interval in seconds")
    p.add_argument(
        "--include-root",
        action="append",
        default=[],
        help="Extra root to crawl (repeatable), e.g. --include-root C:\\ --include-root C:\\Users\\Novac\\iCloudDrive",
    )
    p.add_argument(
        "--include-only-roots",
        action="store_true",
        help="Only crawl roots provided by --include-root (skip MASTER_ROOT_REGISTRY.json)",
    )
    return p.parse_args()


_LOCK_FILE = ROOT / "run" / "ecosystem_fabric_engine.lock"


def _acquire_singleton_lock() -> None:
    """Prevent duplicate instances. Exits 0 immediately if this script is already running."""
    import atexit
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
            if pid != os.getpid():
                os.kill(pid, 0)  # raises OSError if process is gone
                print(f"[singleton] ecosystem_fabric_engine already running as PID {pid} — exiting.", flush=True)
                raise SystemExit(0)
        except (ValueError, OSError):
            pass  # stale lock
    _LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: _LOCK_FILE.unlink(missing_ok=True))


def main() -> int:
    _acquire_singleton_lock()
    args = parse_args()
    engine = EcosystemFabricEngine(
        include_root_paths=args.include_root or [],
        use_master_registry=not args.include_only_roots,
    )

    if not args.daemon:
        snap = engine.run_once()
        relevant = read_json(engine.relevant_inventory_file, {}).get("total_hits", 0)
        print(f"[ecosystem] snapshot: {safe_rel(engine.snapshot_file)}")
        print(f"[ecosystem] roots: {snap.get('root_inventory', {}).get('total_roots', 0)}")
        print(f"[ecosystem] relevant_hits: {relevant}")
        return 0

    print(f"[ecosystem] daemon started interval={args.interval_sec}s")
    while True:
        try:
            snap = engine.run_once()
            changed = snap.get("frozen_delta", {}).get("changed_root_count", 0)
            print(f"[ecosystem] {now_utc()} changed_roots={changed}")
        except Exception as exc:
            print(f"[ecosystem] cycle error: {exc}")
        time.sleep(max(5, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
